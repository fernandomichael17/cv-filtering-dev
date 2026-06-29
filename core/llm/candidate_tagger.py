"""Candidate Tagger — Ekstraksi tags dan skills kandidat menggunakan LLM.

Menyediakan fungsi untuk menganalisis riwayat kandidat dan menghasilkan
tags CV, keahlian (hard/soft skills), serta tags per pengalaman kerja.
"""
import logging
import json
import re
from core.llm.client import call_llm, parse_json_response

logger = logging.getLogger(__name__)


# Kata penjelas umum yang sering muncul pada nama keahlian/sertifikasi
# yang jika dihapus tidak akan merusak arti utama keahlian.
SKILL_EXPLANATORY_WORDS = {
    "software", "programming", "developer", "framework", "library", "database", 
    "system", "sertifikasi", "certification", "certified", "training", 
    "pelatihan", "kursus", "course", "bootcamp", "associate", "professional", 
    "expert", "madya", "pratama", "utama", "kompetensi", "staff", "analyst", 
    "engineer", "specialist", "administration", "administrator"
}


def clean_explanatory_words(skill: str) -> str:
    """Membersihkan kata penjelas umum dari nama keahlian untuk menyisakan kata kunci inti.

    Mengganti simbol tertentu dengan spasi, memecah kata, dan membuang kata
    yang termasuk dalam kata penjelas generik.

    Parameter:
        skill (str): Nama keahlian mentah dalam huruf kecil.

    Return:
        str: Nama keahlian yang telah dibersihkan.
    """
    cleaned = skill.lower().replace("&", " ").replace("-", " ")
    words = cleaned.split()
    cleaned_words = [w for w in words if w not in SKILL_EXPLANATORY_WORDS and len(w) > 1]
    return " ".join(cleaned_words)


def validate_and_refine_candidate_tags(parsed: dict, profile_text: str) -> dict:
    """Memvalidasi dan menyaring tag/skill hasil ekstraksi LLM terhadap teks profil asli.

    Menghapus skill atau tag yang dideteksi sebagai halusinasi karena tidak
    disebutkan sama sekali di teks profil asli kandidat (riwayat kerja/pendidikan/pelatihan).

    Parameter:
        parsed (dict): Hasil ekstraksi JSON dari LLM.
        profile_text (str): Teks profil asli kandidat.

    Return:
        dict: Hasil ekstraksi yang telah dimurnikan.
    """
    if not profile_text:
        return parsed

    profile_lower = profile_text.lower()

    # 1. Validasi Hard Skills menggunakan Kamus Sinonim & Fallback Generik
    from core.utils.skill_synonyms import get_skill_synonyms
    
    hard_skills_raw = parsed.get("skills", {}).get("hard_skill", "")
    if hard_skills_raw:
        skills_list = [s.strip() for s in hard_skills_raw.split(",") if s.strip()]
        valid_skills = []
        for skill in skills_list:
            skill_lower = skill.lower()
            
            # Cari semua varian nama/sinonim untuk keahlian ini
            synonyms = get_skill_synonyms(skill_lower)
            
            is_valid = False
            for syn in synonyms:
                syn_lower = syn.lower()
                
                # Gunakan regex word boundary untuk kata kunci pendek (panjang <= 4)
                if len(syn_lower) <= 4:
                    pattern = re.compile(rf"\b{re.escape(syn_lower)}\b")
                    if pattern.search(profile_lower):
                        is_valid = True
                        break
                else:
                    if syn_lower in profile_lower:
                        is_valid = True
                        break
            
            # Fallback 1: Pembersihan Kata Penjelas Generik (Clean Explanatory Words)
            if not is_valid:
                cleaned_skill = clean_explanatory_words(skill_lower)
                if cleaned_skill:
                    if len(cleaned_skill) <= 4:
                        pattern = re.compile(rf"\b{re.escape(cleaned_skill)}\b")
                        if pattern.search(profile_lower):
                            is_valid = True
                    else:
                        if cleaned_skill in profile_lower:
                            is_valid = True

            # Fallback 2: Pencocokan Token Kata Kunci Penting (Important Token Matching)
            if not is_valid:
                for syn in synonyms:
                    syn_cleaned = clean_explanatory_words(syn)
                    if not syn_cleaned:
                        continue
                    tokens = syn_cleaned.split()
                    important_tokens = [t for t in tokens if len(t) >= 3]
                    if not important_tokens:
                        continue
                    
                    all_tokens_present = True
                    for token in important_tokens:
                        if len(token) <= 4:
                            pattern = re.compile(rf"\b{re.escape(token)}\b")
                            if not pattern.search(profile_lower):
                                all_tokens_present = False
                                break
                        else:
                            if token not in profile_lower:
                                all_tokens_present = False
                                break
                    if all_tokens_present:
                        is_valid = True
                        break
            
            if is_valid:
                valid_skills.append(skill)

        parsed["skills"]["hard_skill"] = ", ".join(valid_skills)

    # 2. Validasi CV Tags (Kategori Makro)
    cv_tags_raw = parsed.get("cv_tags", "")
    if cv_tags_raw:
        tags_list = [t.strip() for t in cv_tags_raw.split(",") if t.strip()]
        valid_tags = []
        for tag in tags_list:
            tag_lower = tag.lower()

            # Lewati validasi untuk bidang makro industri umum agar tidak terhapus
            broad_fields = {"it", "hr", "sales", "marketing", "operations", "engineering", "finance"}
            if tag_lower in broad_fields:
                valid_tags.append(tag)
                continue

            if len(tag_lower) <= 4:
                pattern = re.compile(rf"\b{re.escape(tag_lower)}\b")
                if pattern.search(profile_lower):
                    valid_tags.append(tag)
            else:
                if tag_lower in profile_lower:
                    valid_tags.append(tag)

        parsed["cv_tags"] = ", ".join(valid_tags)

    return parsed


CANDIDATE_TAGGER_PROMPT = """You are an HR assistant. Extract professional tags and skills from the candidate's profile.

Candidate Profile:
{profile_text}

Return ONLY valid JSON with no preamble, explanations, or markdown backticks:
{{
  "cv_tags": "IT, Web Development, PHP, Laravel",
  "skills": {{
    "hard_skill": "PHP, Laravel, MySQL",
    "soft_skill": "Problem Solving, Teamwork",
    "language": "Indonesian, English"
  }},
  "experience_tags": [
    {{
      "work_id": 1,
      "tags": "IT & Software, Web Developer, PHP, Laravel"
    }}
  ]
}}

Rules:
1. cv_tags: A comma-separated list of 3-5 high-level professional tags representing the candidate's core expertise.
2. hard_skill: Comma-separated list of technical/hard skills, tools, methodologies, or core certifications/competencies found in candidate experiences, education, or training (e.g., "PHP, Excel, Accounting, Data Science, Taxation").
3. soft_skill: Comma-separated list of soft skills (e.g., "Communication, Leadership").
4. language: Comma-separated list of languages spoken.
5. experience_tags: For EACH work experience in the profile (identified by work_id), provide:
   - work_id: The integer ID of the work experience.
   - tags: A comma-separated combination of:
     * Broad industry category (choose from: "IT & Software", "Finance & Accounting", "Marketing & PR", "HR & General Affairs", "Sales & Business Development", "Engineering & Manufacturing", "Operations & Supply Chain", "Legal & Compliance", "Creative & Design", "Customer Service", "Administration", "Education").
     * Specific job role/title (e.g., "Backend Developer", "Accounting Staff").
     * Key technologies/skills used in that job (ONLY if explicitly mentioned).
     Example: "IT & Software, Web Developer, PHP, MySQL"
6. CRITICAL: Only extract skills, certifications, and technologies that are EXPLICITLY mentioned in the text. Do NOT infer, guess, or assume any tools or technologies. If the work description is vague (e.g., "handles IT tasks") and there are no specific tools, certifications, or training mentioned in the entire profile, set hard_skill to empty string "" and only include the industry category and role in experience_tags.
7. If no specific tools are mentioned in an experience, only include industry and role: "IT & Software, IT Staff" (no technology tags).
"""

def _build_profile_text(candidate) -> str:
    """Menyusun teks rangkuman profil kandidat dari data pendidikan, pengalaman, dan pelatihan.

    Teks riwayat pekerjaan dibersihkan dari tag HTML dan dibatasi hanya untuk
    maksimal 3 riwayat kerja terbaru guna menghemat token input.

    Parameter:
        candidate: Objek kandidat (Require ORM).

    Return:
        str: Rangkuman profil teks terstruktur.
    """
    from core.llm.jd_parser import clean_html
    lines = []
    
    # Rangkuman Pendidikan
    lines.append("=== EDUCATION ===")
    educations = getattr(candidate, "educations", []) or []
    for edu in educations:
        inst = getattr(edu, "institutionname", "Unknown")
        major = getattr(edu, "major", "") or ""
        if major.strip():
            lines.append(f"- Institution: {inst} | Major: {major.strip()}")
        
    # Rangkuman Pengalaman Kerja (Tanpa Nama Perusahaan) - Terbatas 3 riwayat terbaru
    lines.append("\n=== WORK EXPERIENCE ===")
    work_experiences = getattr(candidate, "work_experiences", []) or []
    
    # Urutkan berdasarkan endyear/startyear terbaru
    sorted_exp = sorted(
        work_experiences,
        key=lambda x: (getattr(x, "endyear", 0) or 0, getattr(x, "startyear", 0) or 0),
        reverse=True
    )[:3]
    
    for exp in sorted_exp:
        work_id = getattr(exp, "workid", 0)
        joblevel = getattr(exp, "joblevel", "Unknown")
        jobdesk = getattr(exp, "jobdesk", "") or ""
        
        # Bersihkan HTML tag dan spasi berlebih
        cleaned_jobdesk = clean_html(jobdesk)
        
        if cleaned_jobdesk.strip() or joblevel.strip():
            lines.append(f"- Experience ID: {work_id}")
            lines.append(f"  Role/Title: {joblevel.strip()}")
            if cleaned_jobdesk.strip():
                lines.append(f"  Description: {cleaned_jobdesk.strip()}")
            
    # Rangkuman Pelatihan
    lines.append("\n=== TRAINING & CERTIFICATION ===")
    trainings = getattr(candidate, "trainings", []) or []
    for t in trainings:
        tname = getattr(t, "trainingname", "") or ""
        if tname.strip():
            lines.append(f"- Training/Cert: {tname.strip()}")
        
    return "\n".join(lines)


async def tag_candidate(candidate) -> dict:
    """Mengekstrak tag CV, keahlian, dan tag pengalaman kerja dari profil kandidat menggunakan LLM.

    Jika profil kandidat tidak memiliki riwayat pendidikan, pengalaman kerja, dan pelatihan,
    maka proses pemanggilan LLM dilewati dan mengembalikan data kosong secara terprogram.

    Parameter:
        candidate: Objek kandidat (Require ORM).

    Return:
        dict: Hasil ekstraksi berupa tag terstruktur.
    """
    educations = getattr(candidate, "educations", []) or []
    work_experiences = getattr(candidate, "work_experiences", []) or []
    trainings = getattr(candidate, "trainings", []) or []
    
    # Empty Profile Guard
    if not educations and not work_experiences and not trainings:
        logger.info("Profil kandidat kosong. Melewati pemanggilan LLM untuk require_id=%d", candidate.requireid)
        return {
            "cv_tags": "",
            "skills": {"hard_skill": "", "soft_skill": "", "language": ""},
            "experience_tags": []
        }

    profile_text = _build_profile_text(candidate)
    prompt = CANDIDATE_TAGGER_PROMPT.format(profile_text=profile_text)
    messages = [{"role": "user", "content": prompt}]
    
    try:
        raw_response = await call_llm(messages, max_tokens=768, temperature=0.1)
        try:
            parsed = parse_json_response(raw_response)
        except json.JSONDecodeError as jde:
            logger.warning(
                "Gagal mendekode JSON hasil candidate tagger pada percobaan pertama (temp=0.1): %s. Mencoba kembali dengan temp=0.2...",
                str(jde)
            )
            raw_response = await call_llm(messages, max_tokens=768, temperature=0.2)
            parsed = parse_json_response(raw_response)
            
        # Validasi struktur minimal
        if "cv_tags" not in parsed:
            parsed["cv_tags"] = ""
        if "skills" not in parsed:
            parsed["skills"] = {"hard_skill": "", "soft_skill": "", "language": ""}
        if "experience_tags" not in parsed:
            parsed["experience_tags"] = []

        # Memurnikan dan memvalidasi hasil ekstraksi terhadap profile_text untuk mencegah halusinasi
        parsed = validate_and_refine_candidate_tags(parsed, profile_text)
            
        return parsed
    except Exception as e:
        logger.error("Gagal melakukan tagging kandidat: %s", e)
        raise ValueError(f"Gagal tagging kandidat: {e}") from e
