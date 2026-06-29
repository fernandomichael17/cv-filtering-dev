"""Modul Evaluasi Pengalaman Kerja Individu & Rumpun Pendidikan (P16)."""

import logging
import re
from datetime import datetime
from app.config import settings
from core.filtering.semantic_matcher import semantic_matcher
from core.filtering.taxonomy.field_compatibility import get_match_type, BROAD_CATEGORIES, _are_fields_compatible
from core.filtering.taxonomy.skills_evaluator import _check_skills_match

from core.filtering.isco_normalizer import normalize_to_isco

logger = logging.getLogger(__name__)

def _extract_role_from_tags(tags_str: str | None) -> str | None:
    """Extract the specific job role (tag ke-2) from tags_jobs string.

    tags_jobs format: "<bidang>, <jabatan>" e.g. "IT, Backend Developer"
    We want the second tag (jabatan/role).
    """
    if not tags_str:
        return None

    parts = [p.strip() for p in tags_str.split(",")]
    if len(parts) >= 2:
        return parts[1]  # Tag ke-2 = jabatan spesifik
    elif len(parts) == 1 and parts[0]:
        return parts[0]  # Fallback: use the only tag available
    return None




def _calc_experience_months(exp) -> float:
    """Calculate experience duration in months from a work experience record."""
    start_date = getattr(exp, "startdate", None)
    end_date = getattr(exp, "enddate", None)
    start_year = getattr(exp, "startyear", None)
    end_year = getattr(exp, "endyear", None)

    if start_date and end_date:
        return max(0, (end_date - start_date).days / 30.0)
    elif start_year and end_year:
        return max(0, (end_year - start_year) * 12)
    elif start_year and getattr(exp, "iscurrent", False):
        return max(0, (datetime.now().year - start_year) * 12)
    return 0




def _clean_job_title_for_major_relevance(job_title: str) -> str:
    """Membersihkan level jabatan dari judul lowongan pekerjaan untuk pencocokan jurusan.

    Menghapus kata-kata tingkatan jabatan (seperti 'junior', 'senior', 'staf') agar perbandingan
    rumpun berfokus pada keilmuan fungsional.

    Parameter:
        job_title (str): Judul posisi pekerjaan yang ditargetkan.

    Return:
        str: Judul pekerjaan yang sudah bersih dari level jabatan.
    """
    if not job_title:
        return ""
    keywords = [
        "junior", "senior", "staf", "staff", "assistant", "asisten", "lead", 
        "head", "officer", "executive", "associate", "intern", "magang", "trainee"
    ]
    cleaned = job_title.lower().strip()
    for kw in keywords:
        cleaned = re.sub(rf"\b{re.escape(kw)}\b", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return job_title.lower().strip()
    return cleaned




def _check_major_relevance(educations: list | None, job_title: str, job_tags: list[str] | None) -> bool:
    """Memeriksa kesesuaian jurusan pendidikan tertinggi kandidat dengan lowongan kerja.

    Menggunakan kombinasi aturan kecocokan rumpun fungsional (deterministik) untuk menyelaraskan
    penilaian lintas industri sebelum beralih ke pencocokan semantik (Multilingual-E5).

    Parameter:
        educations (list | None): Riwayat pendidikan kandidat.
        job_title (str): Judul lowongan kerja yang ditargetkan.
        job_tags (list[str] | None): Kumpulan tag persyaratan dari lowongan.

    Return:
        bool: True jika jurusan relevan, False jika tidak.
    """
    if not educations:
        return False
    from core.filtering.hard_filter import _get_highest_education, _clean_major_for_semantic
    _, _, major, _ = _get_highest_education(educations)
    if not major:
        return False
        
    clean_major = _clean_major_for_semantic(major)
    clean_job = _clean_job_title_for_major_relevance(job_title)
    
    # 1. Aturan Kecocokan Rumpun Deterministik (Heuristik - menggunakan nama jurusan yang sudah dibersihkan)
    IT_MAJORS = {"sistem informasi", "informasi", "informatika", "komputer", "rekayasa perangkat lunak", "perangkat lunak", "teknologi"}
    IT_JOBS = {"developer", "programmer", "software", "network", "system", "database", 
               "data science", "data scientist", "data analyst", "system analyst", "cloud", 
               "devops", "it support", "it admin", "it", "web"}

    FINANCE_MAJORS = {"akuntansi", "accounting", "keuangan", "finance", "perbankan", "perpajakan", "taxation"}
    FINANCE_JOBS = {"accountant", "accounting", "finance", "perpajakan", "tax", "auditor", "bookkeeper", "kasir", "teller"}

    HR_MAJORS = {"psikologi", "psychology", "manajemen sumber daya manusia", "msdm", "human resource management", "hubungan industrial"}
    HR_JOBS = {"hr", "human resource", "recruiter", "talent acquisition", "training", "people development"}

    CIVIL_MAJORS = {"sipil", "civil", "bangunan"}
    CIVIL_JOBS = {"civil engineer", "civil", "sipil", "konstruksi", "construction"}

    BUSINESS_MAJORS = {"manajemen", "management", "administrasi bisnis", "business administration", "pemasaran", "marketing", "komunikasi", "communication studies"}
    BUSINESS_JOBS = {"sales", "marketing", "business development", "account executive", "telemarketing", "customer service", "admin"}

    # Cek kecocokan deterministik
    is_it_match = any(m in clean_major for m in IT_MAJORS) and any(j in clean_job for j in IT_JOBS)
    is_finance_match = any(m in clean_major for m in FINANCE_MAJORS) and any(j in clean_job for j in FINANCE_JOBS)
    is_hr_match = any(m in clean_major for m in HR_MAJORS) and any(j in clean_job for j in HR_JOBS)
    is_civil_match = any(m in clean_major for m in CIVIL_MAJORS) and any(j in clean_job for j in CIVIL_JOBS)
    is_business_match = any(m in clean_major for m in BUSINESS_MAJORS) and any(j in clean_job for j in BUSINESS_JOBS)
    
    if is_it_match or is_finance_match or is_hr_match or is_civil_match or is_business_match:
        return True
        
    # 2. Fallback Semantik jika aturan heuristik tidak terpenuhi
    targets = [clean_job]
    if job_tags:
        for tag in job_tags:
            cleaned_tag = _clean_job_title_for_major_relevance(tag)
            if cleaned_tag and cleaned_tag not in targets:
                targets.append(cleaned_tag)
                
    max_sim = 0.0
    for target in targets:
        sim_score, _ = semantic_matcher.calculate_max_similarity(clean_major, [target])
        if sim_score > max_sim:
            max_sim = sim_score
            
    return max_sim >= 0.86




def _is_general_trainee_program(job_title: str) -> bool:
    """Check if the job title indicates a general management trainee, intern, or fresh graduate program."""
    if not job_title:
        return False
    normalized = f" {job_title.strip().lower()} "
    keywords = [
        "management trainee",
        " mt ",
        "trainee",
        "intern",
        "magang",
        "fresh graduate program",
        "graduate development",
        "odp",
        "sdp",
        "pps",
        "officer development",
        "staff development",
    ]
    return any(kw in normalized for kw in keywords)




def _has_experience_skills_match(exp, job_tags: list[str] | None) -> bool:
    """
    Memeriksa apakah deskripsi tugas (jobdesk) atau tag dari suatu riwayat pengalaman kandidat
    mengandung keahlian/spesialisasi yang relevan dengan syarat lowongan.
    Digunakan untuk meresolusi ambiguitas jabatan umum makro (seperti "IT" atau "IT Staff").
    
    Parameter:
        exp (RequireWorkExperience): Objek riwayat pengalaman kerja kandidat.
        job_tags (list[str]): Tag dari lowongan pekerjaan.
        
    Return:
        bool: True jika terdapat kecocokan keahlian, False jika tidak.
    """
    if not exp or not job_tags:
        return False
        
    jobdesk = getattr(exp, "jobdesk", None)
    jobdesk_lower = jobdesk.lower() if jobdesk else ""
    
    exp_tags_obj = getattr(exp, "experience_tags", None)
    tags_str = getattr(exp_tags_obj, "tags", None) if exp_tags_obj else ""
    tags_lower = tags_str.lower() if tags_str else ""
    
    # Gabungkan seluruh konteks teks pengalaman ini
    exp_text = f"{jobdesk_lower} {tags_lower}".strip()
    if not exp_text:
        return False
        
    # Ekstraksi keahlian spesifik lowongan (abaikan kategori besar menggunakan BROAD_CATEGORIES global)
    job_tags_clean = [t.strip().lower() for t in job_tags if t.strip()]
    specific_job_tags = job_tags_clean[1:] if len(job_tags_clean) > 1 else job_tags_clean
    
    job_skills = [t for t in specific_job_tags if t not in BROAD_CATEGORIES]
    if not job_skills:
        return False
        
    # 1. Pencocokan langsung (kata kunci substring)
    for skill in job_skills:
        if skill in exp_text:
            return True
        # Pengecekan per kata
        words = skill.split()
        if len(words) > 1 and all(w in exp_text for w in words):
            return True
            
    # 2. Pencocokan semantik (E5 similarity fallback)
    from core.filtering.semantic_matcher import semantic_matcher
    for skill in job_skills:
        # Pengecekan pada jobdesk jika ada
        if jobdesk_lower:
            sim, _ = semantic_matcher.calculate_max_similarity(skill, [jobdesk_lower])
            if sim >= settings.SIMILARITY_THRESHOLD_TAXONOMY_EXP_SKILLS:
                return True
                
    return False




def _evaluate_single_experience(
    exp,
    job_code: str,
    job_title: str,
    job_tags: list[str] | None,
    job_tags_clean: list[str],
) -> tuple[float, str, str, str | None]:
    """Mengevaluasi satu riwayat pengalaman kerja kandidat secara mendalam.

    Fungsi ini menghitung durasi pengalaman kerja dalam bulan, menentukan tingkat kecocokan 
    taksonomi ISCO, menerapkan peningkatan status kecocokan berbasis skill khusus (upgrade otomatis),
    serta memvalidasi kesesuaian bidang (domain/field compatibility) dengan proteksi agar tidak 
    diturunkan statusnya jika ada kecocokan skill khusus.

    Parameter:
        exp (any): Objek riwayat pengalaman kerja kandidat dari database.
        job_code (str): Kode taksonomi ISCO dari lowongan pekerjaan.
        job_title (str): Judul posisi pekerjaan lowongan.
        job_tags (list[str] | None): Daftar tag keahlian dari lowongan.
        job_tags_clean (list[str]): Daftar tag keahlian lowongan yang sudah dibersihkan.

    Return:
        tuple[float, str, str, str | None]: Tuple berisi durasi (bulan), tingkat kecocokan (match_type),
                                            kode taksonomi pengalaman (exp_code), dan judul posisi pengalaman.
    """
    months = _calc_experience_months(exp)
    tags_str = None
    exp_tags_obj = getattr(exp, "experience_tags", None)
    if exp_tags_obj:
        tags_str = getattr(exp_tags_obj, "tags", None)

    role = _extract_role_from_tags(tags_str)
    exp_code = normalize_to_isco(role) if role else "unknown"

    match_type = get_match_type(job_code, exp_code, job_title=job_title, exp_title=role)
    
    # Deteksi kecocokan skill pada deskripsi pengalaman kerja
    has_skills_match = _has_experience_skills_match(exp, job_tags)

    # Resolusi Ambiguitas Jabatan IT Makro berbasis Skill Kerja
    raw_match = get_match_type(job_code, exp_code)
    if match_type == "loosely_related" and raw_match in ("exact", "related"):
        if has_skills_match:
            match_type = raw_match
    elif match_type in ("loosely_related", "unrelated", "unknown"):
        # UPGRADE OTOMATIS (SKILL-BASED): Jika secara taksonomi tidak sejalan, namun kandidat memiliki
        # aktivitas konkret di jobdesk-nya yang mengandung skill utama dari job_tags,
        # maka angkat statusnya ke 'related'.
        if has_skills_match:
            match_type = "related"

    # Validasi kesesuaian bidang (domain/field) untuk menghindari kecocokan taksonomi palsu
    exp_field = None
    if tags_str:
        parts = [p.strip().lower() for p in tags_str.split(",")]
        if len(parts) >= 1:
            exp_field = parts[0]
    
    job_field = job_tags_clean[0] if job_tags_clean else None
    if job_field and exp_field and not _are_fields_compatible(job_field, exp_field):
        # Proteksi upgrade berbasis skill: jangan diturunkan ke unrelated jika ada kecocokan skill
        if not has_skills_match:
            match_type = "unrelated"

    return months, match_type, exp_code, role




def _evaluate_all_experiences(
    candidate_experiences: list,
    job_code: str,
    job_title: str,
    job_tags: list[str] | None,
    job_tags_clean: list[str],
) -> tuple[float, float, str, list[str], list[str]]:
    """Mengevaluasi seluruh riwayat pengalaman kerja kandidat secara akumulatif.

    Iterasi seluruh pengalaman kerja kandidat menggunakan helper `_evaluate_single_experience`
    untuk mengumpulkan total masa kerja, masa kerja yang relevan (dengan bobot 100% untuk exact
    dan 50% untuk related), serta riwayat kode taksonomi dan peran.

    Parameter:
        candidate_experiences (list): Daftar riwayat pengalaman kerja kandidat.
        job_code (str): Kode taksonomi ISCO dari lowongan pekerjaan.
        job_title (str): Judul posisi pekerjaan lowongan.
        job_tags (list[str] | None): Daftar tag keahlian dari lowongan.
        job_tags_clean (list[str]): Daftar tag keahlian lowongan yang sudah dibersihkan.

    Return:
        tuple[float, float, str, list[str], list[str]]: Tuple berisi total bulan relevan,
            total bulan kerja keseluruhan, tingkat kecocokan terbaik (best_match_type),
            daftar kode taksonomi kandidat, dan daftar nama peran kandidat.
    """
    relevant_months = 0.0
    total_months = 0.0
    candidate_codes = []
    candidate_roles = []
    best_match_type = "unrelated"
    match_priority = {"exact": 4, "related": 3, "loosely_related": 2, "unknown": 1, "unrelated": 0}

    for exp in candidate_experiences:
        months, match_type, exp_code, role = _evaluate_single_experience(
            exp, job_code, job_title, job_tags, job_tags_clean
        )
        total_months += months
        candidate_codes.append(exp_code)
        if role:
            candidate_roles.append(role)

        if match_priority[match_type] > match_priority[best_match_type]:
            best_match_type = match_type

        if match_type == "exact":
            relevant_months += months
        elif match_type == "related":
            # Jika transisi dari Profesional (ISCO awal 2) ke Manajerial (ISCO awal 1)
            is_transition = (
                job_code and exp_code and
                job_code.startswith("1") and exp_code.startswith("2")
            )
            if is_transition:
                relevant_months += (months * 0.75)
            else:
                relevant_months += (months * 0.5)

    return relevant_months, total_months, best_match_type, candidate_codes, candidate_roles



