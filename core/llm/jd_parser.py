"""JD Parser — Single LLM call.

Parses a free-text job description into structured requirements
and extracts 3 key tags (bidang, keahlian, tools) in a single LLM call.
"""

import html
import logging
import re
import json

from core.llm.client import call_llm, parse_json_response

logger = logging.getLogger(__name__)


def clean_html(raw_html: str) -> str:
    """
    Membersihkan tag HTML dan mendekode entitas HTML dari string mentah,
    serta mempertahankan spasi pemformatan.

    Parameter:
        raw_html (str): Teks HTML mentah yang akan dibersihkan.

    Return:
        str: Teks bersih tanpa tag HTML.
    """
    if not raw_html:
        return ""
    
    # 1. Ganti tag block/break dengan newline untuk mencegah kata-kata menempel
    # e.g., "Python</p><p>SQL" -> "Python\nSQL"
    text = re.sub(r'<(?:p|div|tr|h[1-6]|li|ul|ol|br\s*/?)[^>]*>', '\n', raw_html, flags=re.IGNORECASE)
    
    # 2. Hapus semua tag HTML yang tersisa (tag inline seperti <b>, <i>, <span>, dll) tanpa menambahkan spasi
    text = re.sub(r'<[^>]+>', '', text)
    
    # 3. Dekode entitas HTML (e.g. &nbsp; -> \xa0, &amp; -> &)
    text = html.unescape(text)
    
    # 4. Ganti non-breaking spaces (\xa0) dengan spasi standar
    text = text.replace('\xa0', ' ')
    
    # 5. Bersihkan spasi berlebih dalam baris dan hapus baris kosong
    lines = []
    for line in text.splitlines():
        # Gabungkan spasi/tab berlebih dalam satu baris
        cleaned_line = re.sub(r'[ \t]+', ' ', line).strip()
        if cleaned_line:
            lines.append(cleaned_line)
            
    return '\n'.join(lines)


JD_PARSE_PROMPT = """You are an HR assistant. Extract the requirements from the following job description into a JSON format.

Job Description:
{jd_text}

Return ONLY valid JSON with no preamble, explanations, or markdown backticks:
{{
  "min_education": "S1",
  "allowed_majors": ["Teknik Informatika", "Ilmu Komputer"],
  "major_flexibility": "flexible",
  "min_experience_years": 2,
  "max_experience_years": null,
  "preferred_min_experience_years": 2,
  "preferred_max_experience_years": null,
  "min_age": 21,
  "max_age": 35,
  "min_gpa": 3.0,
  "marital_status": "Belum Menikah",
  "required_skills": ["Python", "SQL"],
  "preferred_skills": ["Docker"],
  "required_certifications": ["AWS Certified Solutions Architect"],
  "preferred_certifications": ["TOEFL", "PMP"],
  "tags": ["IT", "Machine Learning", "Python"],
  "budget": 10000000,
  "placement_outside_jakarta": false,
  "standardized_title": "Machine Learning Engineer"
}}

Rules:
- min_education: choose one of SMA, D3, S1, S2, S3. CRITICAL: If the Job Description states a slash-separated or range/alternative education requirement (e.g., "D3/S1", "SMA/D3", "S1 atau S2"), you MUST select the LOWEST education level mentioned as the absolute minimum requirement (e.g. "D3/S1" -> "D3", "SMA/D3" -> "SMA", "S1 atau S2" -> "S1").
- allowed_majors: List of specific university majors/degrees required (e.g. "Teknik Informatika", "Hukum"). If JD mentions specific degrees like "Law degree", extract the corresponding major (e.g., "Hukum"). If open to all majors or not specified, leave empty []. CRITICAL: If the Job Description uses abbreviations or acronyms (e.g., "DKV", "HI", "TI", "SI", "T. Sipil"), you MUST expand them to their full formal names in Indonesian (e.g., "Desain Komunikasi Visual", "Hubungan Internasional", "Teknik Informatika", "Sistem Informasi", "Teknik Sipil").
- major_flexibility: "strict" (must match exactly) or "flexible" (related majors are ok)
- min_experience_years: ABSOLUTE required minimum years of experience (integer). CRITICAL: If the JD mentions "fresh graduate dipersilakan" or "fresh grad ok", this MUST be 0 regardless of any other numbers mentioned.
- max_experience_years: ABSOLUTE required maximum years. If the JD is for "Intern" or "Magang", this MUST be 1. Otherwise, DO NOT set this UNLESS explicitly stated with keywords like "maksimal 3 tahun", "tidak lebih dari", "up to". If no strict upper limit is specified, MUST be null.
- preferred_min_experience_years: The lower bound of the PREFERRED experience range. (e.g. if JD says "Fresh graduate dipersilakan, pengalaman 1-2 tahun", set this to 1). If not stated, set to the same value as min_experience_years.
- preferred_max_experience_years: The upper bound of the PREFERRED experience range. (e.g. if JD says "pengalaman 3-5 tahun", set this to 5). If no upper range is mentioned, MUST be null.
- min_age: explicitly required minimum age (integer). If not stated, MUST be null.
- max_age: explicitly required maximum age (integer). If not stated, MUST be null.
- min_gpa: explicitly required minimum GPA out of 4.0 (float). If not stated, MUST be null.
- marital_status: explicitly required marital status, choose one of: "Belum Menikah" (Single), "Menikah" (Married), or null if not explicitly stated.
- required_skills: Strictly required tools, professional skills, or core domain knowledge explicitly mentioned in the JD (e.g. "Python", "Ms. Excel", "HRIS", "Undang-Undang Ketenagakerjaan", "Komunikasi", "Negosiasi", "Industrial Relation", "Mengemudi"). Do NOT include generic subjective adjectives like "jujur", "pekerja keras", "bertanggung jawab", but DO include key professional/technical skills.
- preferred_skills: PREFERRED technical skills, tools, or professional competencies considered a plus.
- required_certifications: STRICTLY REQUIRED professional certifications or licenses (e.g., "Ahli K3 Umum", "SIM A"). Put mandatory certs here, not in required_skills.
- preferred_certifications: PREFERRED certifications or licenses, not mandatory but a plus. Put optional certs here.
- tags: MUST be an array containing exactly 3 strings, respectively:
  1. Job field (e.g., "IT", "Finance", "HR", "Marketing", "Engineering")
  2. Specific expertise in that field (e.g., "Machine Learning", "Web Development", "HR Generalist")
  3. Main tools/technologies used (e.g., "Python", "SAP", "HRIS", "AutoCAD")
- budget: explicitly stated maximum salary budget/limit for this job in IDR (integer). If stated in millions, convert to full integer (e.g. "Gaji up to 15jt" or "Budget max 15.000.000" -> 15000000). If not stated, MUST be null.
- placement_outside_jakarta: boolean (true/false). Set to true if the job description explicitly mentions requiring or demanding candidates to be willing to be relocated or placed outside Jakarta or outside Jabodetabek or all over Indonesia (e.g. "bersedia ditempatkan di luar Jakarta", "bersedia ditempatkan di seluruh Indonesia", "willing to be relocated outside Jakarta"). Otherwise, set to false.
- standardized_title: Based on the combined job title, description, and specifications/responsibilities, write 1 standard, clean job title (in 2-3 words, either in standard English or Indonesian) that best represents the actual role. E.g. if the title is "Networking Supervisor" but the duties are managing call center agents, this should be "Supervisor Call Center" or "Call Center Supervisor".
- If not explicitly stated, use reasonable defaults EXCEPT for min_experience_years which MUST be 0, and min_age, max_age, min_gpa, max_experience_years, preferred_max_experience_years, and marital_status which MUST be null if missing.
-
EXAMPLE 1 (IT JD):
JD: "Dibutuhkan Senior Backend Engineer. Gaji up to 15.000.000. Minimal lulusan S1 Teknik Informatika. Pengalaman minimal 3 tahun, maksimal 6 tahun. Usia 25-35 tahun. Harus menguasai Python dan Django, memiliki pengalaman dengan PostgreSQL. Diutamakan yang memahami AWS dan Docker."
Output:
{{
  "min_education": "S1",
  "allowed_majors": ["Teknik Informatika"],
  "major_flexibility": "flexible",
  "min_experience_years": 3,
  "max_experience_years": 6,
  "preferred_min_experience_years": 3,
  "preferred_max_experience_years": 6,
  "min_age": 25,
  "max_age": 35,
  "min_gpa": null,
  "marital_status": null,
  "required_skills": ["Python", "Django", "PostgreSQL"],
  "preferred_skills": ["AWS", "Docker"],
  "required_certifications": [],
  "preferred_certifications": [],
  "tags": ["IT", "Web Development", "Python"],
  "budget": 15000000,
  "placement_outside_jakarta": false,
  "standardized_title": "Backend Engineer"
}}

EXAMPLE 2 (Non-IT Safety JD):
JD: "Lowongan HSE Officer. Pendidikan min D3 Teknik atau Kesehatan Kerja. Fresh graduate dipersilakan, pengalaman 1-2 tahun. Wajib memiliki sertifikasi Ahli K3 Umum yang masih aktif dan memiliki SIM A. Diutamakan memiliki sertifikasi ISO 45001 atau NEBOSH. Harus sehat jasmani dan bisa bekerja dalam tim. Bersedia ditempatkan di site project luar Jawa/luar Jakarta."
Output:
{{
  "min_education": "D3",
  "allowed_majors": ["Teknik", "Kesehatan Kerja"],
  "major_flexibility": "flexible",
  "min_experience_years": 0,
  "max_experience_years": null,
  "preferred_min_experience_years": 1,
  "preferred_max_experience_years": 2,
  "min_age": null,
  "max_age": null,
  "min_gpa": null,
  "marital_status": null,
  "required_skills": [],
  "preferred_skills": [],
  "required_certifications": ["Ahli K3 Umum", "SIM A"],
  "preferred_certifications": ["ISO 45001", "NEBOSH"],
  "tags": ["Engineering", "HSE", "K3"],
  "budget": null,
  "placement_outside_jakarta": true,
  "standardized_title": "HSE Officer"
}}

EXAMPLE 3 (HR/Generalist JD):
JD: "Lowongan Kerja HRGA Supervisor. Pendidikan minimal S1 Psikologi, Manajemen Sumber Daya Manusia, atau Administrasi Bisnis. Minimal 5 tahun pengalaman kerja di bidang HRGA/HR Generalist di perusahaan manufaktur. Pemahaman yang kuat tentang undang-undang ketenagakerjaan dan industrial relation. Kemampuan komunikasi yang baik, baik lisan maupun tertulis, dan kemampuan bernegosiasi yang andal. Pengetahuan tentang penggunaan HRIS. Mampu berbahasa Mandarin menjadi nilai tambah."
Output:
{{
  "min_education": "S1",
  "allowed_majors": ["Psikologi", "Manajemen Sumber Daya Manusia", "Administrasi Bisnis"],
  "major_flexibility": "flexible",
  "min_experience_years": 5,
  "max_experience_years": null,
  "preferred_min_experience_years": 5,
  "preferred_max_experience_years": null,
  "min_age": null,
  "max_age": null,
  "min_gpa": null,
  "marital_status": null,
  "required_skills": ["Undang-Undang Ketenagakerjaan", "HRIS", "Komunikasi", "Negosiasi", "Industrial Relation"],
  "preferred_skills": ["Mandarin"],
  "required_certifications": [],
  "preferred_certifications": [],
  "tags": ["HR", "HR Generalist", "HRIS"],
  "budget": null,
  "placement_outside_jakarta": false,
  "standardized_title": "HRGA Supervisor"
}}"""


def validate_and_refine_jd(parsed: dict, jd_text: str) -> dict:
    """
    Memvalidasi dan memurnikan hasil ekstraksi persyaratan Job Description.

    Langkah-langkah:
    1. Memeriksa apakah setiap required_skill atau salah satu sinonimnya muncul di jd_text
       menggunakan pencocokan kata utuh (regex word-boundary).
    2. Jika tidak ditemukan dalam jd_text -> diturunkan (demote) ke preferred_skills untuk mencegah halusinasi.
    3. Memastikan key required_certifications, preferred_certifications, dan compatible_categories terdefinisi.
    4. Membersihkan max_experience_years secara deterministik jika tidak ada kata kunci pembatas atas yang eksplisit.

    Parameter:
        parsed (dict): Data hasil ekstraksi JSON dari LLM.
        jd_text (str): Teks Job Description asli yang sudah dibersihkan.

    Return:
        dict: Data persyaratan Job Description yang telah dimurnikan.
    """
    jd_text_lower = jd_text.lower()
    
    required_skills = parsed.get("required_skills") or []
    preferred_skills = parsed.get("preferred_skills") or []
    refined_required = []
    
    # Impor get_skill_synonyms untuk pencocokan sinonim keahlian
    from core.utils.skill_synonyms import get_skill_synonyms
    
    for skill in required_skills:
        skill_clean = skill.strip().lower()
        if not skill_clean:
            continue
            
        variations = get_skill_synonyms(skill)
        found = False
        
        # Lakukan pengecekan pencocokan kata utuh untuk setiap sinonim keahlian
        for var in variations:
            var_clean = var.strip().lower()
            if not var_clean:
                continue
            # Regex untuk mencocokkan kata utuh (symbol-safe word boundaries)
            pattern = rf"(?<![a-zA-Z0-9]){re.escape(var_clean)}(?![a-zA-Z0-9])"
            if re.search(pattern, jd_text_lower):
                found = True
                break
                
        if found:
            refined_required.append(skill)
        else:
            logger.warning("Demoting skill '%s' to preferred_skills because it was not found in JD text", skill)
            if skill not in preferred_skills:
                preferred_skills.append(skill)
                
    parsed["required_skills"] = refined_required
    parsed["preferred_skills"] = preferred_skills

    # ── Validasi allowed_majors ──────────────────────────────────────────────
    # 1. Bersihkan output generik LLM (misal: "Semua Jurusan", "All Majors").
    # 2. Log warning jika jurusan tidak ditemukan di teks JD (potensi halusinasi),
    #    tapi TIDAK men-demote karena jurusan sering ditulis implisit di JD Indonesia.
    allowed_majors = parsed.get("allowed_majors") or []
    if isinstance(allowed_majors, str):
        allowed_majors = [m.strip() for m in allowed_majors.split(",") if m.strip()]

    generic_majors = {
        "semua jurusan", "all majors", "any major", "segala jurusan",
        "semua bidang", "all fields", "all disciplines",
    }
    cleaned_majors = [
        m for m in allowed_majors
        if m.strip().lower() not in generic_majors
    ]
    if len(cleaned_majors) < len(allowed_majors):
        logger.info(
            "Membersihkan jurusan generik dari allowed_majors: %s -> %s",
            allowed_majors, cleaned_majors
        )

    # Log warning untuk jurusan yang mungkin halusinasi (tidak muncul di teks JD)
    from core.utils.major_mapping import MAJOR_SYNONYMS
    for major in cleaned_majors:
        major_lower = major.strip().lower()
        # Kumpulkan variasi: nama asli + sinonim dari MAJOR_SYNONYMS
        variations = {major_lower}
        # Cek apakah major adalah value di MAJOR_SYNONYMS, ambil semua key yang mengarah ke sana
        for syn_key, syn_val in MAJOR_SYNONYMS.items():
            if syn_val.strip().lower() == major_lower or syn_key == major_lower:
                variations.add(syn_key)
                variations.add(syn_val.strip().lower())

        found_in_jd = False
        for var in variations:
            if not var:
                continue
            pattern = rf"(?<![a-zA-Z0-9]){re.escape(var)}(?![a-zA-Z0-9])"
            if re.search(pattern, jd_text_lower):
                found_in_jd = True
                break

        if not found_in_jd:
            logger.warning(
                "Jurusan '%s' dari LLM tidak ditemukan di teks JD (potensi halusinasi, tetap dipertahankan)", major
            )

    parsed["allowed_majors"] = cleaned_majors
    
    if "required_certifications" not in parsed:
        parsed["required_certifications"] = []
    if "preferred_certifications" not in parsed:
        parsed["preferred_certifications"] = []
    if "compatible_categories" not in parsed:
        parsed["compatible_categories"] = []
        
    # ── Koreksi Pengalaman Kerja dengan Regex (Hybrid Parser) ────────────────
    try:
        clean_jd_text = re.sub(r'\s+', ' ', jd_text_lower)
        
        # 1. Cari range pengalaman (e.g. 1-2 tahun, 3 s/d 5 thn)
        range_pattern = r'(?:pengalaman|experience|kerja|selama|min|minimal)\s+[^.]{0,60}?\b(\d+)\s*(?:-|s/d|sampai)\s*(\d+)\s*(?:tahun|thn|th|years|yr|year)\b'
        range_match = re.search(range_pattern, clean_jd_text)
        
        # Cek kata kunci fresh graduate
        fresh_keywords = ["fresh graduate", "fresh grad", "lulusan baru", "tanpa pengalaman"]
        is_fresh_ok = any(kw in clean_jd_text for kw in fresh_keywords)
        
        if range_match:
            r_min = int(range_match.group(1))
            r_max = int(range_match.group(2))
            if r_min < 17:  # Membedakan dengan umur
                if is_fresh_ok:
                    parsed["min_experience_years"] = 0
                else:
                    parsed["min_experience_years"] = r_min
                parsed["preferred_min_experience_years"] = r_min
                parsed["preferred_max_experience_years"] = r_max
                parsed["max_experience_years"] = None
                logger.info("Regex corrected experience range to min: %d, pref_min: %d, pref_max: %d", parsed["min_experience_years"], r_min, r_max)
        else:
            # 2. Cari nilai tunggal (e.g. min 3 tahun)
            single_pattern = r'(?:pengalaman|experience|kerja|selama|min|minimal)\s+[^.]{0,60}?\b(\d+)\s*(?:tahun|thn|th|years|yr|year)\b'
            single_match = re.search(single_pattern, clean_jd_text)
            if single_match:
                s_val = int(single_match.group(1))
                if s_val < 17:
                    if is_fresh_ok:
                        parsed["min_experience_years"] = 0
                    else:
                        parsed["min_experience_years"] = s_val
                    parsed["preferred_min_experience_years"] = s_val
                    parsed["preferred_max_experience_years"] = None
                    parsed["max_experience_years"] = None
                    logger.info("Regex corrected experience to min: %d", parsed["min_experience_years"])
    except Exception as e:
        logger.warning("Gagal melakukan koreksi regex pengalaman kerja: %s", e)

    if "preferred_min_experience_years" not in parsed:
        parsed["preferred_min_experience_years"] = parsed.get("min_experience_years", 0)
    if "preferred_max_experience_years" not in parsed:
        parsed["preferred_max_experience_years"] = None
    if "budget" not in parsed:
        parsed["budget"] = None
    if "placement_outside_jakarta" not in parsed:
        parsed["placement_outside_jakarta"] = False

    # Pemurnian max_experience_years secara deterministik
    intern_keywords = ["intern", "magang"]
    is_intern = any(kw in jd_text_lower for kw in intern_keywords)
    
    if is_intern:
        parsed["max_experience_years"] = 1
        logger.info("Programmatically set max_experience_years to 1 because job is an internship.")
    else:
        max_exp = parsed.get("max_experience_years")
        if max_exp is not None:
            try:
                # Batasi pencarian max_keywords hanya pada kalimat yang relevan dengan masa kerja/pengalaman kerja
                max_keywords = ["max", "maks", "maximum", "maksimal", "not more", "tidak lebih", "up to", "hingga", "batas", "paling lama"]
                exp_sentences = []
                for sentence in re.split(r'[.\n]', jd_text_lower):
                    if any(w in sentence for w in ["tahun", "thn", "pengalaman", "experience", "kerja"]):
                        exp_sentences.append(sentence)
                exp_context = " ".join(exp_sentences)
                
                if not any(kw in exp_context for kw in max_keywords):
                    parsed["max_experience_years"] = None
                    logger.info("Programmatically set max_experience_years to None because no maximum keywords found in experience context.")
            except Exception as e:
                logger.warning("Failed to validate max_experience_years: %s", e)
                parsed["max_experience_years"] = None

    # Validasi dan perkuat tipe data agar scoring tidak error
    parsed = _sanitize_parsed_types(parsed)
            
    return parsed


def _sanitize_parsed_types(parsed: dict) -> dict:
    """Memvalidasi dan mengkonversi tipe data hasil parsing LLM secara defensif.

    LLM terkadang mengembalikan string ("dua tahun") untuk field numerik
    atau integer untuk field yang seharusnya list. Fungsi ini memastikan
    setiap field memiliki tipe data yang benar sebelum masuk ke pipeline scoring.

    Parameter:
        parsed (dict): Data hasil parsing LLM.

    Return:
        dict: Data dengan tipe data yang sudah divalidasi.
    """
    # Field numerik (int/float) — konversi string ke angka, fallback ke default
    numeric_fields = {
        "min_experience_years": (0, int),
        "max_experience_years": (None, int),
        "preferred_min_experience_years": (0, int),
        "preferred_max_experience_years": (None, int),
        "min_age": (None, int),
        "max_age": (None, int),
        "min_gpa": (None, float),
        "budget": (None, int),
    }

    for field, (default, target_type) in numeric_fields.items():
        val = parsed.get(field)
        if val is None:
            parsed[field] = default
            continue
        if isinstance(val, (int, float)):
            try:
                parsed[field] = target_type(val)
            except (ValueError, TypeError):
                parsed[field] = default
            continue
        # val adalah string — coba ekstrak angka darinya
        if isinstance(val, str):
            cleaned = re.sub(r"[^\d.]", "", val)
            if cleaned:
                try:
                    parsed[field] = target_type(float(cleaned))
                except (ValueError, TypeError):
                    logger.warning("Gagal mengkonversi field '%s' dari '%s', menggunakan default %s", field, val, default)
                    parsed[field] = default
            else:
                logger.warning("Field '%s' berisi teks tanpa angka: '%s', menggunakan default %s", field, val, default)
                parsed[field] = default
            continue
        # Tipe tidak dikenal
        parsed[field] = default

    # Validasi rentang wajar (P5)
    # 1. Batasan Umur (min_age: 16-65, max_age: 18-70)
    min_age = parsed.get("min_age")
    if min_age is not None:
        if not (16 <= min_age <= 65):
            logger.warning("Nilai min_age '%s' di luar rentang wajar (16-65). Mereset ke None.", min_age)
            parsed["min_age"] = None

    max_age = parsed.get("max_age")
    if max_age is not None:
        if not (18 <= max_age <= 70):
            logger.warning("Nilai max_age '%s' di luar rentang wajar (18-70). Mereset ke None.", max_age)
            parsed["max_age"] = None

    if parsed.get("min_age") is not None and parsed.get("max_age") is not None:
        if parsed["min_age"] > parsed["max_age"]:
            logger.warning("Nilai min_age (%s) lebih besar dari max_age (%s). Mereset keduanya ke None.", parsed["min_age"], parsed["max_age"])
            parsed["min_age"] = None
            parsed["max_age"] = None

    # 2. Batasan Pengalaman Kerja (min_experience_years: 0-40, max_experience_years: 1-50)
    min_exp = parsed.get("min_experience_years")
    if min_exp is not None:
        if not (0 <= min_exp <= 40):
            logger.warning("Nilai min_experience_years '%s' di luar rentang wajar (0-40). Mereset ke 0.", min_exp)
            parsed["min_experience_years"] = 0

    max_exp = parsed.get("max_experience_years")
    if max_exp is not None:
        if not (1 <= max_exp <= 50):
            logger.warning("Nilai max_experience_years '%s' di luar rentang wajar (1-50). Mereset ke None.", max_exp)
            parsed["max_experience_years"] = None

    if parsed.get("min_experience_years") is not None and parsed.get("max_experience_years") is not None:
        if parsed["min_experience_years"] > parsed["max_experience_years"]:
            logger.warning(
                "Nilai min_experience_years (%s) lebih besar dari max_experience_years (%s). Mereset max_experience_years ke None.",
                parsed["min_experience_years"], parsed["max_experience_years"]
            )
            parsed["max_experience_years"] = None

    # Sanity check: max_experience_years tidak boleh lebih kecil dari rentang preferred
    if parsed.get("max_experience_years") is not None:
        pref_max = parsed.get("preferred_max_experience_years")
        pref_min = parsed.get("preferred_min_experience_years")
        if (pref_max is not None and parsed["max_experience_years"] < pref_max) or \
           (pref_min is not None and parsed["max_experience_years"] < pref_min):
            logger.warning(
                "Kontradiksi logika: max_experience_years (%s) lebih kecil dari rentang preferensi. Mereset max_experience_years ke None.",
                parsed["max_experience_years"]
            )
            parsed["max_experience_years"] = None

    # 3. Batasan Pengalaman Kerja Pilihan (preferred_min_experience_years: 0-40, preferred_max_experience_years: 1-50)
    pref_min_exp = parsed.get("preferred_min_experience_years")
    if pref_min_exp is not None:
        if not (0 <= pref_min_exp <= 40):
            logger.warning("Nilai preferred_min_experience_years '%s' di luar rentang wajar (0-40). Mereset ke 0.", pref_min_exp)
            parsed["preferred_min_experience_years"] = 0

    pref_max_exp = parsed.get("preferred_max_experience_years")
    if pref_max_exp is not None:
        if not (1 <= pref_max_exp <= 50):
            logger.warning("Nilai preferred_max_experience_years '%s' di luar rentang wajar (1-50). Mereset ke None.", pref_max_exp)
            parsed["preferred_max_experience_years"] = None

    if parsed.get("preferred_min_experience_years") is not None and parsed.get("preferred_max_experience_years") is not None:
        if parsed["preferred_min_experience_years"] > parsed["preferred_max_experience_years"]:
            logger.warning(
                "Nilai preferred_min_experience_years (%s) lebih besar dari preferred_max_experience_years (%s). Mereset preferred_max_experience_years ke None.",
                parsed["preferred_min_experience_years"], parsed["preferred_max_experience_years"]
            )
            parsed["preferred_max_experience_years"] = None

    # 4. Batasan GPA (min_gpa: 0.0-4.0)
    min_gpa = parsed.get("min_gpa")
    if min_gpa is not None:
        if not (0.0 <= min_gpa <= 4.0):
            logger.warning("Nilai min_gpa '%s' di luar rentang wajar (0.0-4.0). Mereset ke None.", min_gpa)
            parsed["min_gpa"] = None

    # Field list — pastikan selalu berupa list of strings
    list_fields = [
        "allowed_majors", "required_skills", "preferred_skills",
        "required_certifications", "preferred_certifications",
        "compatible_categories", "tags",
    ]
    for field in list_fields:
        val = parsed.get(field)
        if val is None:
            parsed[field] = []
        elif isinstance(val, str):
            # LLM kadang mengembalikan "Python, SQL" sebagai string tunggal
            parsed[field] = [s.strip() for s in val.split(",") if s.strip()]
        elif not isinstance(val, list):
            parsed[field] = []

    # Field string — pastikan bukan angka/list
    string_fields = ["min_education", "major_flexibility", "marital_status", "standardized_title"]
    for field in string_fields:
        val = parsed.get(field)
        if val is not None and not isinstance(val, str):
            parsed[field] = str(val) if val else None

    # Field boolean — pastikan bernilai boolean
    bool_fields = ["placement_outside_jakarta"]
    for field in bool_fields:
        val = parsed.get(field)
        if val is None:
            parsed[field] = False
        elif isinstance(val, bool):
            parsed[field] = val
        elif isinstance(val, str):
            parsed[field] = val.lower() in ("true", "1", "yes", "y")
        elif isinstance(val, int):
            parsed[field] = val == 1
        else:
            parsed[field] = False

    return parsed


async def parse_job_description(jd_text: str) -> dict:
    """
    Menganalisis teks Job Description dan mengekstrak persyaratan terstruktur serta tag bidang.
    Proses ini berjalan dalam satu kali pemanggilan LLM untuk meminimalkan latensi.

    Parameter:
        jd_text (str): Teks Job Description bebas dari HRD.

    Return:
        dict: Persyaratan pekerjaan terstruktur yang siap dipakai untuk penyaringan.

    Exception:
        ValueError: Jika respons LLM tidak dapat didekode menjadi format JSON.
    """
    jd_clean = clean_html(jd_text)
    prompt = JD_PARSE_PROMPT.format(jd_text=jd_clean)
    messages = [{"role": "user", "content": prompt}]

    try:
        raw_response = await call_llm(messages, max_tokens=1024, temperature=0.1)
        try:
            parsed = parse_json_response(raw_response)
        except json.JSONDecodeError as jde:
            logger.warning(
                "Gagal mendekode JSON hasil JD parser pada percobaan pertama (temp=0.1): %s. Mencoba kembali dengan temp=0.2...",
                str(jde)
            )
            raw_response = await call_llm(messages, max_tokens=1024, temperature=0.2)
            parsed = parse_json_response(raw_response)
            
        refined = validate_and_refine_jd(parsed, jd_clean)
        logger.info("JD parsed successfully. Tags: %s", refined.get("tags", []))
        return refined
    except Exception as e:
        logger.error("Failed to parse JD: %s | Raw: %s", e, raw_response if 'raw_response' in dir() else 'N/A')
        raise ValueError(f"Gagal parsing JD: {e}") from e

