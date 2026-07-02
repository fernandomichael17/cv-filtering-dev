"""Rule-based hard filtering for candidates.

Applies six filters in sequence:
1. Education level — candidate's highest level >= minimum required
2. Major matching — exact, group-based, or partial string match
3. Experience years — total months / 12 >= minimum required
4. Age — candidate age within min/max bounds
5. Marital status — candidate status matches requirement
6. Required certifications — candidate has all mandatory certs
"""

import logging
import re

from app.config import settings
from core.utils.major_mapping import EDUCATION_HIERARCHY, EDU_ID_TO_STR, MAJOR_GROUPS, MAJOR_SYNONYMS

logger = logging.getLogger(__name__)


def _get_education_level(level_str: str | None) -> int:
    """Convert education level string to numeric hierarchy value."""
    if not level_str:
        return 0
    # Normalize: strip whitespace, uppercase
    normalized = level_str.strip().upper()
    # Try direct match first
    for key, value in EDUCATION_HIERARCHY.items():
        if key.upper() == normalized:
            return value
    # Fuzzy: check if any key is contained in the string
    for key, value in EDUCATION_HIERARCHY.items():
        if key.upper() in normalized:
            return value
    return 0


def _get_highest_education(educations: list) -> tuple[int, str | None, str | None, str | None]:
    """Find the highest education level from a list of education records.

    Returns:
        Tuple of (level_value, level_str, major, institution).
    """
    best_level = 0
    best_level_str = None
    best_major = None
    best_institution = None

    for edu in educations:
        edu_id = getattr(edu, "education_id", None)
        level_str = EDU_ID_TO_STR.get(edu_id, "")
        
        level_val = _get_education_level(level_str)
        if level_val > best_level:
            best_level = level_val
            best_level_str = level_str
            best_major = getattr(edu, "major", None)
            best_institution = getattr(edu, "institutionname", None)

    return best_level, best_level_str, best_major, best_institution


from core.utils.major_matcher import (
    normalize_major as _normalize_major,
    get_major_group as _get_major_group,
    clean_major_for_semantic as _clean_major_for_semantic,
    check_major_match,
)

def _get_total_experience_years(work_experiences: list) -> float:
    """Menghitung total pengalaman kerja dalam tahun dari daftar riwayat pekerjaan.

    Menggunakan algoritma timeline merge untuk mencegah penghitungan ganda
    pada periode kerja yang tumpang tindih (overlap). Jika kandidat bekerja
    di 2 tempat secara bersamaan (misal 2020-2023 dan 2021-2024),
    hasilnya 4 tahun (bukan 7 tahun).

    Parameter:
        work_experiences (list): Daftar objek pengalaman kerja dari database.

    Return:
        float: Total pengalaman kerja dalam tahun (sudah di-merge).
    """
    from datetime import datetime, date

    # Kumpulkan semua interval (start_date, end_date) dalam satuan date
    intervals = []
    for exp in work_experiences:
        start_date = getattr(exp, "startdate", None)
        end_date = getattr(exp, "enddate", None)
        start_year = getattr(exp, "startyear", None)
        end_year = getattr(exp, "endyear", None)

        s, e = None, None

        if start_date and end_date:
            s = start_date if isinstance(start_date, date) else start_date.date() if hasattr(start_date, 'date') else None
            e = end_date if isinstance(end_date, date) else end_date.date() if hasattr(end_date, 'date') else None
        elif start_year and end_year:
            s = date(int(start_year), 1, 1)
            e = date(int(end_year), 1, 1)
        elif start_year and getattr(exp, "iscurrent", False):
            s = date(int(start_year), 1, 1)
            e = date(datetime.now().year, datetime.now().month, datetime.now().day)

        if s and e and e >= s:
            intervals.append((s, e))

    if not intervals:
        return 0.0

    # Merge overlapping intervals
    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0]]
    for current_start, current_end in intervals[1:]:
        last_start, last_end = merged[-1]
        if current_start <= last_end:
            # Overlap terdeteksi, gabungkan interval
            merged[-1] = (last_start, max(last_end, current_end))
        else:
            merged.append((current_start, current_end))

    # Hitung total hari dari interval yang sudah di-merge
    total_days = sum((e - s).days for s, e in merged)
    return total_days / 365.25


def _parse_dateofbirth(dob_raw) -> 'datetime | None':
    """Mengkonversi dateofbirth dari varchar ke datetime.

    Database aktual menyimpan dateofbirth sebagai VARCHAR dengan
    format yang bervariasi (YYYY-MM-DD, DD/MM/YYYY, dll).

    Parameter:
        dob_raw: Nilai dateofbirth dari database (str atau datetime).

    Return:
        datetime | None: Objek datetime atau None jika parsing gagal.
    """
    if not dob_raw:
        return None
    from datetime import datetime as dt

    # Jika sudah datetime, langsung kembalikan
    if isinstance(dob_raw, dt):
        return dob_raw

    dob_str = str(dob_raw).strip()
    if not dob_str:
        return None

    formats = [
        "%Y-%m-%d",      # 1996-05-15
        "%d/%m/%Y",      # 15/05/1996
        "%d-%m-%Y",      # 15-05-1996
        "%Y/%m/%d",      # 1996/05/15
        "%d %B %Y",      # 15 May 1996
        "%d %b %Y",      # 15 May 1996 (abbreviated)
        "%Y-%m-%d %H:%M:%S",  # 1996-05-15 00:00:00
    ]
    for fmt in formats:
        try:
            return dt.strptime(dob_str, fmt)
        except ValueError:
            continue

    logger.warning("Gagal parsing dateofbirth: '%s'", dob_str)
    return None


def _calculate_age(dob) -> int | None:
    """Menghitung umur dari tanggal lahir (mendukung varchar dan datetime).

    Parameter:
        dob: Nilai dateofbirth dari database (str atau datetime).

    Return:
        int | None: Umur dalam tahun atau None jika tidak bisa dihitung.
    """
    from datetime import datetime
    parsed = _parse_dateofbirth(dob)
    if not parsed:
        return None
    today = datetime.today()
    return today.year - parsed.year - ((today.month, today.day) < (parsed.month, parsed.day))


def _match_marital_status(candidate_status: str | None, required_status: str | None) -> bool:
    """Check if candidate's marital status matches requirements with synonym normalization.
    
    Note: marital_status is filled manually (not from CV extraction).
    If the field is empty/None, we pass the candidate (benefit of the doubt).
    """
    if not required_status:
        return True
    if not candidate_status:
        return True  # Data belum diisi manual → loloskan
    
    cand_norm = candidate_status.strip().lower()
    req_norm = required_status.strip().lower()
    
    # Map common synonyms
    single_synonyms = ["belum menikah", "belum kawin", "lajang", "single", "tidak menikah"]
    married_synonyms = ["menikah", "kawin", "married", "sudah menikah", "sudah kawin"]
    
    is_cand_single = any(s in cand_norm for s in single_synonyms) or cand_norm == "single"
    is_cand_married = any(m in cand_norm for m in married_synonyms) or cand_norm == "married"
    
    is_req_single = any(s in req_norm for s in single_synonyms) or req_norm == "single"
    is_req_married = any(m in req_norm for m in married_synonyms) or req_norm == "married"
    
    if is_req_single:
        return is_cand_single
    if is_req_married:
        return is_cand_married
        
    return req_norm in cand_norm or cand_norm in req_norm


def _match_gender(candidate_gender: str | None, required_gender: str | None) -> bool:
    """Memeriksa apakah gender kandidat sesuai dengan persyaratan lowongan.

    Parameter:
        candidate_gender: Gender kandidat (misal: "Laki-laki", "Perempuan").
        required_gender: Gender yang disyaratkan (misal: "Laki-laki", "Male").

    Return:
        bool: True jika cocok atau tidak ada persyaratan.
    """
    if not required_gender:
        return True
    if not candidate_gender:
        return True  # Data belum diisi → loloskan

    cand = candidate_gender.strip().lower()
    req = required_gender.strip().lower()

    male_synonyms = ["laki-laki", "laki", "pria", "male", "l"]
    female_synonyms = ["perempuan", "wanita", "female", "f", "p"]

    cand_male = any(s == cand for s in male_synonyms)
    cand_female = any(s == cand for s in female_synonyms)
    req_male = any(s == req for s in male_synonyms)
    req_female = any(s == req for s in female_synonyms)

    if req_male:
        return cand_male
    if req_female:
        return cand_female

    return cand == req


def _is_driver_license(cert_name: str) -> bool:
    """Check if a certification name represents a driver's license (e.g. SIM A, SIM C)."""
    normalized = cert_name.strip().lower()
    if "surat izin mengemudi" in normalized or "driver" in normalized or "driving" in normalized:
        return True
    
    # Split words and check if "sim" is one of them
    words = re.findall(r'\b\w+\b', normalized)
    return "sim" in words


def _match_certification(cert_required: str, candidate_training_names: list[str]) -> tuple[bool, str]:
    """Match a required certification against candidate's training names.

    Uses 3-stage matching:
    1. Exact match (case-insensitive)
    2. Substring match (both directions, min 4 chars to avoid false positives)
    3. Semantic similarity fallback (threshold >= 0.85, strict for hard filter)

    Args:
        cert_required: The certification name required by the job.
        candidate_training_names: List of candidate training names (lowercase).

    Returns:
        Tuple of (is_match, match_type) where match_type is
        'exact', 'substring', 'semantic', or 'none'.
    """
    cert_lower = cert_required.strip().lower()

    # 1. Exact match
    for name in candidate_training_names:
        if cert_lower == name:
            return True, "exact"

    # 2. Substring match (both directions)
    # Min length guard: only substring match if the shorter string is >= 4 chars
    # to prevent "SIM A" from matching "Ahli K3 Umum" etc.
    for name in candidate_training_names:
        shorter = min(len(cert_lower), len(name))
        if shorter >= 4 and (cert_lower in name or name in cert_lower):
            return True, "substring"

    # 3. Semantic similarity fallback (strict threshold for hard filter)
    if candidate_training_names:
        from core.filtering.semantic_matcher import semantic_matcher
        sim, _ = semantic_matcher.calculate_max_similarity(
            cert_required, candidate_training_names
        )
        if sim >= settings.SIMILARITY_THRESHOLD_CERTIFICATION:
            return True, "semantic"

    return False, "none"


def apply_hard_filters(
    candidates: list,
    requirements: dict,
) -> tuple[list, list[dict]]:
    """
    Menerapkan penyaringan mutlak (hard filters) berbasis aturan terhadap daftar kandidat.

    Penyaringan meliputi:
    0. Gender (jika disyaratkan).
    1. Jenjang pendidikan minimum.
    2. Jurusan pendidikan (khusus untuk mode strict).
    3. Batas minimum dan maksimum pengalaman kerja (dalam tahun).
    4. Batas umur minimum dan maksimum.
    5. Status pernikahan (jika disyaratkan).
    5.5. IPK minimum.
    6. Sertifikasi wajib.

    Parameter:
        candidates (list): Daftar kandidat (objek Require ORM) yang dimuat dari database.
        requirements (dict): Persyaratan pekerjaan terstruktur hasil ekstraksi LLM.

    Return:
        Tuple[list, list[dict]]: Pasangan daftar kandidat yang lolos (passed) dan daftar kandidat yang tereliminasi (eliminated).
    """
    min_education = requirements.get("min_education", "SMA")
    allowed_majors = requirements.get("allowed_majors", [])
    major_flexibility = requirements.get("major_flexibility", "flexible")
    min_experience_years = requirements.get("min_experience_years")
    if min_experience_years is None:
        min_experience_years = 0.0
    else:
        try:
            min_experience_years = float(min_experience_years)
        except (ValueError, TypeError):
            min_experience_years = 0.0

    max_experience_years = requirements.get("max_experience_years")
    if max_experience_years is not None:
        try:
            max_experience_years = float(max_experience_years)
        except (ValueError, TypeError):
            max_experience_years = None

    # Type coercion for LLM-parsed values
    if isinstance(allowed_majors, str):
        allowed_majors = [m.strip() for m in allowed_majors.split(",") if m.strip()]

    min_age = requirements.get("min_age")
    max_age = requirements.get("max_age")
    if isinstance(min_age, str):
        digits = re.sub(r'\D', '', min_age)
        min_age = int(digits) if digits else None
    if isinstance(max_age, str):
        digits = re.sub(r'\D', '', max_age)
        max_age = int(digits) if digits else None

    req_marital_status = requirements.get("marital_status")
    req_gender = requirements.get("gender")

    min_gpa = requirements.get("min_gpa")
    if min_gpa is not None:
        try:
            min_gpa = float(min_gpa)
        except (ValueError, TypeError):
            min_gpa = None

    min_edu_level = _get_education_level(min_education)

    passed = []
    eliminated = []

    for candidate in candidates:
        name = f"{candidate.firstname or ''} {candidate.lastname or ''}".strip()
        rid = candidate.requireid

        # 0. Gender check
        if req_gender:
            cand_gender = getattr(candidate, "gender", None)
            if cand_gender and not _match_gender(cand_gender, req_gender):
                eliminated.append({
                    "require_id": rid,
                    "candidate_name": name,
                    "reason": (
                        f"[Gender] Gender kandidat ({cand_gender}) "
                        f"tidak sesuai dengan ketentuan '{req_gender}'."
                    ),
                })
                continue

        # 1. Education level check
        highest_level, level_str, major, institution = _get_highest_education(
            candidate.educations
        )
        if highest_level < min_edu_level:
            eliminated.append({
                "require_id": rid,
                "candidate_name": name,
                "reason": (
                    f"[Pendidikan] Jenjang pendidikan kandidat ({level_str or 'tidak diketahui'}) "
                    f"tidak memenuhi syarat minimum lowongan ({min_education})."
                ),
            })
            continue

        # 2. Major match check (Strict only)
        if allowed_majors and major_flexibility == "strict":
            if not major:
                eliminated.append({
                    "require_id": rid,
                    "candidate_name": name,
                    "reason": f"[Jurusan] Kandidat tidak memiliki data jurusan di CV, sedangkan lowongan mensyaratkan jurusan khusus (strict): {', '.join(allowed_majors)}."
                })
                continue
            
            is_match = check_major_match(major, allowed_majors)
            
            if not is_match:
                eliminated.append({
                    "require_id": rid,
                    "candidate_name": name,
                    "reason": f"[Jurusan] Jurusan kandidat '{major}' tidak sesuai dengan daftar jurusan yang disyaratkan (strict): {', '.join(allowed_majors)}."
                })
                continue

        # 3. Experience years check
        total_years = _get_total_experience_years(candidate.work_experiences)
            
        if total_years < min_experience_years:
            eliminated.append({
                "require_id": rid,
                "candidate_name": name,
                "reason": (
                    f"[Masa Kerja] Total pengalaman kerja ({total_years:.1f} tahun) kurang dari "
                    f"minimum {min_experience_years:.1f} tahun yang disyaratkan."
                ),
            })
            continue

        if max_experience_years is not None and total_years > max_experience_years:
            eliminated.append({
                "require_id": rid,
                "candidate_name": name,
                "reason": (
                    f"[Masa Kerja] Total pengalaman kerja ({total_years:.1f} tahun) melebihi "
                    f"batas maksimum {max_experience_years:.1f} tahun yang diperbolehkan."
                ),
            })
            continue



        # 4. Age check
        if min_age is not None or max_age is not None:
            age = _calculate_age(getattr(candidate, "dateofbirth", None))
            if age is None:
                logger.warning(
                    "Kandidat %s (ID: %d) tidak mencantumkan tanggal lahir. Pengecekan umur dilewati.",
                    name, rid,
                )
            else:
                if min_age is not None and age < min_age:
                    eliminated.append({
                        "require_id": rid,
                        "candidate_name": name,
                        "reason": f"[Umur] Usia kandidat ({age} tahun) di bawah batas minimum yang ditentukan ({min_age} tahun).",
                    })
                    continue
                if max_age is not None and age > max_age:
                    eliminated.append({
                        "require_id": rid,
                        "candidate_name": name,
                        "reason": f"[Umur] Usia kandidat ({age} tahun) di atas batas maksimum yang diperbolehkan ({max_age} tahun).",
                    })
                    continue

        # 5. Marital status check
        if req_marital_status:
            cand_marital = getattr(candidate, "marital_status", None)
            if not _match_marital_status(cand_marital, req_marital_status):
                eliminated.append({
                    "require_id": rid,
                    "candidate_name": name,
                    "reason": (
                        f"[Status Pernikahan] Status pernikahan kandidat ({cand_marital or 'tidak diketahui'}) "
                        f"tidak sesuai dengan ketentuan '{req_marital_status}'."
                    ),
                })
                continue
                
        # 5.5 Minimum GPA check
        if min_gpa is not None:
            gpa_val = 0.0
            for edu in candidate.educations:
                score_str = getattr(edu, "score", None)
                if score_str:
                    try:
                        val = float(str(score_str).replace(',', '.'))
                        if val > gpa_val and val <= 4.0:
                            gpa_val = val
                    except ValueError:
                        pass
            
            if gpa_val > 0.0 and gpa_val < min_gpa:
                eliminated.append({
                    "require_id": rid,
                    "candidate_name": name,
                    "reason": f"[IPK] Nilai IPK kandidat ({gpa_val:.2f}) di bawah syarat minimum ({min_gpa:.2f})."
                })
                continue

        # 6. Required certifications check (Bypass driver's licenses)
        required_certs = requirements.get("required_certifications", [])
        if required_certs:
            candidate_training_names = [
                getattr(t, "trainingname", "").strip().lower()
                for t in getattr(candidate, "trainings", []) or []
                if getattr(t, "trainingname", None)
            ]

            # Filter out driver's licenses from hard filtering
            non_driver_required_certs = [
                cert for cert in required_certs if not _is_driver_license(cert)
            ]

            if non_driver_required_certs:
                if not candidate_training_names:
                    eliminated.append({
                        "require_id": rid,
                        "candidate_name": name,
                        "reason": (
                            f"[Sertifikasi] Kandidat tidak memiliki sertifikasi wajib yang disyaratkan lowongan: "
                            f"{', '.join(non_driver_required_certs)}."
                        ),
                    })
                    continue

                unmatched_certs = []
                for cert in non_driver_required_certs:
                    matched, _ = _match_certification(cert, candidate_training_names)
                    if not matched:
                        unmatched_certs.append(cert)

                if unmatched_certs:
                    eliminated.append({
                        "require_id": rid,
                        "candidate_name": name,
                        "reason": (
                            f"[Sertifikasi] Kandidat tidak memiliki sertifikasi wajib berikut: "
                            f"{', '.join(unmatched_certs)}."
                        ),
                    })
                    continue

        passed.append(candidate)

    logger.info(
        "Hard filter: %d passed, %d eliminated out of %d total",
        len(passed), len(eliminated), len(candidates),
    )
    return passed, eliminated
