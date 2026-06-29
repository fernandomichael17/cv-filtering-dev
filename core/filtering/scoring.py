"""Scoring layer for candidates that passed hard filters.

Enhanced scoring with components (max 100 total):
1. Taxonomy Match — job role relevance via ISCO codes (max 25)
2. Experience Surplus — years above minimum (max 10)
3. Education Surplus — level above minimum (max 10)
4. Major Match — exact/group/semantic (max 10)
5. GPA — academic performance (max 5)
6. Certifications — relevance-weighted, not just binary (max 10)
7. Skills Match — required_skills + preferred_skills vs candidate skills (max 20)
8. Project Relevance — project descriptions vs job context (max 10)
9. Jobdesk Relevance — work responsibilities vs job description (bonus, within cap)

Fresh graduate candidates use adaptive weights that prioritize
projects, skills, and education over experience.
"""

import logging

from app.config import settings
from core.filtering.hard_filter import (
    _get_highest_education,
    _get_education_level,
    _get_major_group,
    _normalize_major,
)
from core.filtering.semantic_matcher import semantic_matcher
from core.utils.skill_synonyms import normalize_skill
from core.utils.skill_helper import build_candidate_skills, check_skill_matches

logger = logging.getLogger(__name__)


# ── Helper: Build candidate skill set from all ground-truth sources ──────────

# Catatan: _build_candidate_skills dipindahkan ke core.utils.skill_helper.py untuk mengeliminasi duplikasi.





def _match_skill_semantic(skill: str, candidate_skills: set[str], threshold: float | None = None) -> bool:
    """Memeriksa apakah suatu keahlian cocok dengan daftar keahlian kandidat menggunakan kemiripan semantik.

    Parameter:
        skill (str): Nama keahlian yang dicari.
        candidate_skills (set[str]): Kumpulan nama keahlian kandidat.
        threshold (float | None, opsional): Nilai ambang batas kemiripan. Jika None, menggunakan nilai default dari pengaturan.

    Return:
        bool: True jika tingkat kemiripan semantik lebih besar atau sama dengan threshold, False jika tidak.
    """
    if not candidate_skills:
        return False
    if threshold is None:
        threshold = settings.SIMILARITY_THRESHOLD_SCORING_SKILL

    skill_lower = normalize_skill(skill)
    sim_score, _ = semantic_matcher.calculate_max_similarity(skill_lower, list(candidate_skills))
    return sim_score >= threshold


# ── Component Scorers ────────────────────────────────────────────────────────


def _score_taxonomy(taxonomy_result: dict) -> tuple[float, dict]:
    """
    Menghitung skor kecocokan taksonomi peran pekerjaan (maksimal 25.0).

    Parameter:
        taxonomy_result (dict): Hasil pencocokan taksonomi peran dari Layer 2.

    Return:
        Tuple[float, dict]: Nilai skor komponen taksonomi dan detail pemecahan nilai.
    """
    match_type = taxonomy_result.get("match_type", "unrelated")
    score = 0.0
    if match_type == "exact":
        score = 25.0
    elif match_type == "related":
        score = 17.0
    elif match_type == "skills_match":
        score = 5.0
    elif match_type == "loosely_related":
        score = 3.0

    return score, {"value": match_type, "score": score}



def _score_experience_surplus(requirements: dict, taxonomy_result: dict, skills_match_pct: float = 1.0) -> tuple[float, dict]:
    """Component 2: Relevant Experience Surplus (Max 15)."""
    # Gunakan preferred_min_experience_years sebagai basis surplus jika tersedia.
    # Ini mencegah kandidat mendapat surplus jika pengalaman kurang dari harapan (misal: min mutlak 0, tapi preferensi 1-2 tahun).
    pref_min = requirements.get("preferred_min_experience_years")
    if pref_min is not None:
        try:
            base_exp = float(pref_min)
        except (ValueError, TypeError):
            base_exp = requirements.get("min_experience_years", 0.0)
    else:
        try:
            base_exp = float(requirements.get("min_experience_years", 0.0))
        except (ValueError, TypeError):
            base_exp = 0.0

    relevant_years = taxonomy_result.get("relevant_years", 0.0)
    surplus = max(0.0, relevant_years - base_exp)
    # +3.33 points per surplus year, max 10 (3 years surplus)
    raw_score = min(10.0, surplus * 3.33)

    # Terapkan discount factor berdasarkan skills_match_pct:
    # - skills_match >= 60% -> surplus poin penuh (1.0x)
    # - skills_match 30%-59% -> surplus poin setengah (0.5x)
    # - skills_match < 30% -> surplus poin minimal (0.2x)
    if skills_match_pct >= 0.60:
        discount = 1.0
    elif skills_match_pct >= 0.30:
        discount = 0.5
    else:
        discount = 0.2

    score = raw_score * discount

    return round(score, 1), {
        "value": round(surplus, 1),
        "score": round(score, 1),
        "skills_match_pct": round(skills_match_pct, 2),
        "discount_applied": discount
    }


def _score_education_surplus(candidate, requirements: dict) -> tuple[float, dict]:
    """Component 3: Education Level Surplus (Max 10)."""
    min_edu_str = requirements.get("min_education") or "SMA"
    min_edu_level = _get_education_level(min_edu_str)

    highest_level, level_str, _, _ = _get_highest_education(candidate.educations)

    surplus = max(0, highest_level - min_edu_level)
    # +5 points per level above minimum, max 10
    score = min(10.0, float(surplus * 5))

    return score, {"value": level_str, "score": score}


def _score_major_match(candidate, requirements: dict) -> tuple[float, dict]:
    """
    Menghitung skor kecocokan jurusan kandidat terhadap jurusan yang diperbolehkan (maksimal 10.0).
    Menggunakan normalisasi jurusan untuk mendeteksi sinonim secara akurat sebelum melakukan pencocokan.

    Parameter:
        candidate (Require): Objek kandidat dari database.
        requirements (dict): Persyaratan lowongan kerja.

    Return:
        Tuple[float, dict]: Nilai skor komponen jurusan dan detail pemecahan nilai.
    """
    allowed_majors = requirements.get("allowed_majors") or []
    _, _, major, _ = _get_highest_education(candidate.educations)

    if not allowed_majors:
        return 10.0, {"value": "any_major", "score": 10.0}

    if not major:
        return 0.0, {"value": "none", "score": 0.0}

    major_norm = _normalize_major(major)
    allowed_majors_norm = [_normalize_major(a) for a in allowed_majors]

    # 1. Pencocokan eksak sinonim
    if any(a_norm == major_norm for a_norm in allowed_majors_norm):
        return 10.0, {"value": "exact", "score": 10.0}

    # 2. Pencocokan serumpun (group)
    cand_group = _get_major_group(major_norm)
    if cand_group and any(_get_major_group(a_norm) == cand_group for a_norm in allowed_majors_norm):
        return 7.0, {"value": "group", "score": 7.0}

    # 3. Pencocokan semantik
    sim_score, _ = semantic_matcher.calculate_max_similarity(major_norm, allowed_majors_norm)
    if sim_score >= 0.90:
        return 10.0, {"value": "semantic_exact", "score": 10.0}
    if sim_score >= 0.86:
        return 7.0, {"value": "semantic_group", "score": 7.0}
    if sim_score >= 0.80:
        return 4.0, {"value": "semantic_partial", "score": 4.0}

    # 4. Pencocokan string sebagian (partial)
    for allowed_n in allowed_majors_norm:
        if allowed_n in major_norm or major_norm in allowed_n:
            return 4.0, {"value": "partial", "score": 4.0}

    return 0.0, {"value": "none", "score": 0.0}


def _score_gpa(candidate) -> tuple[float, dict]:
    """Component 5: GPA / Academic Score (Max 5)."""
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

    score = 0.0
    if gpa_val >= 3.5:
        score = 5.0
    elif gpa_val >= 3.0:
        score = 3.0

    return score, {"value": round(gpa_val, 2), "score": score}


def _match_cert_for_scoring(cert: str, training_names: list[str]) -> tuple[bool, str]:
    """Mencocokkan nama sertifikasi dengan daftar pelatihan kandidat untuk penilaian skor.

    Menggunakan pencocokan eksak, substring, lalu fallback semantik (threshold 0.80).

    Parameter:
        cert (str): Nama sertifikasi yang dicari.
        training_names (list[str]): Daftar nama pelatihan kandidat.

    Return:
        Tuple[bool, str]: Status kecocokan (True/False) dan tipe kecocokan ("exact", "substring", "semantic", atau "none").
    """
    cert_lower = cert.strip().lower()

    for name in training_names:
        name_lower = name.strip().lower()
        if cert_lower == name_lower:
            return True, "exact"
        if cert_lower in name_lower or name_lower in cert_lower:
            return True, "substring"

    # Fallback Semantik menggunakan threshold lebih ketat (0.80) untuk menghindari false positive
    if training_names:
        sim, best_match = semantic_matcher.calculate_max_similarity(cert, training_names)
        if sim >= settings.SIMILARITY_THRESHOLD_SCORING_CERT:
            logger.info("Sertifikasi [SEMANTIC] '%s' cocok dengan '%s' (sim=%.2f)", cert, best_match, sim)
            return True, "semantic"

    return False, "none"


def _score_certifications(candidate, requirements: dict) -> tuple[float, dict]:
    """Menghitung skor relevansi sertifikasi kandidat (maksimal 10.0 poin).

    Penilaian dibagi menjadi 3 tingkatan (tier):
    - Tier 1: Sertifikasi wajib (required_certifications) yang cocok — maksimal 5 poin (proporsional).
    - Tier 2: Sertifikasi yang disukai (preferred_certifications) yang cocok — maksimal 3 poin.
    - Tier 3: Bonus sertifikat yang relevan dengan konteks lowongan (threshold similarity 0.65) — maksimal 2 poin.

    Parameter:
        candidate (Require): Objek data kandidat.
        requirements (dict): Persyaratan lowongan pekerjaan.

    Return:
        Tuple[float, dict]: Nilai skor komponen sertifikasi dan rincian data pencocokannya.
    """
    trainings = getattr(candidate, "trainings", []) or []
    if not trainings:
        return 0.0, {
            "count": 0, "required_matched": [],
            "preferred_matched": [], "bonus_relevant": 0, "score": 0.0,
        }

    training_names = [
        getattr(t, "trainingname", "")
        for t in trainings
        if getattr(t, "trainingname", None)
    ]

    if not training_names:
        return 0.0, {
            "count": len(trainings), "required_matched": [],
            "preferred_matched": [], "bonus_relevant": 0, "score": 0.0,
        }

    required_certs = requirements.get("required_certifications", [])
    preferred_certs = requirements.get("preferred_certifications", [])

    score = 0.0
    required_matched = []
    preferred_matched = []
    bonus_relevant = 0

    # ── Tier 1: Sertifikasi wajib (maksimal 5 poin) ──
    if required_certs:
        for cert in required_certs:
            matched, match_type = _match_cert_for_scoring(cert, training_names)
            if matched:
                required_matched.append(f"{cert} ({match_type})")

        match_ratio = len(required_matched) / len(required_certs)
        score += match_ratio * 5.0  # Proporsional max 5 poin

    # ── Tier 2: Sertifikasi yang disukai (maksimal 3 poin) ──
    if preferred_certs:
        for cert in preferred_certs:
            matched, match_type = _match_cert_for_scoring(cert, training_names)
            if matched:
                preferred_matched.append(f"{cert} ({match_type})")

        score += min(3.0, len(preferred_matched) * 1.5)

    # ── Tier 3: Bonus sertifikat relevan dengan konteks lowongan (maksimal 2 poin) ──
    job_context_parts = []
    for skill in requirements.get("required_skills", []):
        job_context_parts.append(skill)
    for skill in requirements.get("preferred_skills", []):
        job_context_parts.append(skill)

    if job_context_parts:
        job_context = ", ".join(job_context_parts)
        # Abaikan sertifikasi yang sudah cocok di Tier 1 & Tier 2 dari perhitungan bonus
        already_matched_lower = set()
        for m in required_matched + preferred_matched:
            cert_name = m.rsplit(" (", 1)[0].lower()
            already_matched_lower.add(cert_name)

        for name in training_names:
            if name.strip().lower() in already_matched_lower:
                continue
            sim, _ = semantic_matcher.calculate_max_similarity(name, [job_context])
            # Naikkan threshold bonus sertifikat ke 0.65 untuk menghindari pencocokan yang terlalu longgar
            if sim >= 0.65:
                bonus_relevant += 1

        score += min(2.0, bonus_relevant * 1.0)
    elif not required_certs and not preferred_certs:
        # Jika lowongan tidak mensyaratkan sertifikasi apa pun → bonus langsung per sertifikat
        score += min(2.0, len(training_names) * 1.0)
        bonus_relevant = len(training_names)

    score = min(10.0, score)

    return score, {
        "count": len(trainings),
        "required_matched": required_matched,
        "preferred_matched": preferred_matched,
        "bonus_relevant": bonus_relevant,
        "score": round(score, 1),
    }


def _score_skills_match(candidate, requirements: dict, job_title: str = "") -> tuple[float, dict]:
    """
    Menghitung skor kecocokan keahlian kandidat dengan persyaratan lowongan (maksimal 15.0).

    Parameter:
        candidate (Require): Objek kandidat dari database.
        requirements (dict): Persyaratan lowongan pekerjaan.
        job_title (str): Judul posisi pekerjaan.

    Return:
        Tuple[float, dict]: Skor kecocokan keahlian dan detail penjelasannya.
    """
    required_skills = requirements.get("required_skills", [])
    preferred_skills = requirements.get("preferred_skills", [])
    candidate_skills = build_candidate_skills(candidate)

    if not required_skills and not preferred_skills:
        # SMART FALLBACK: Jika tidak ada skill dari JD, bangun konteks dari
        # standardized_title + tags + job_title untuk pencocokan yang lebih kaya.
        if not job_title or not candidate_skills:
            return 0.0, {"required_matched": [], "preferred_matched": [], "score": 0.0, "note": "No skills requirement in JD"}

        # Bangun daftar konteks dari semua sumber yang tersedia
        fallback_contexts = []
        std_title = requirements.get("standardized_title")
        if std_title and std_title.strip():
            fallback_contexts.append(std_title.strip())
        if job_title.strip() and job_title.strip() not in fallback_contexts:
            fallback_contexts.append(job_title.strip())
        job_tags = requirements.get("tags") or []
        for tag in job_tags:
            tag_clean = tag.strip()
            if tag_clean and tag_clean not in fallback_contexts:
                fallback_contexts.append(tag_clean)

        if not fallback_contexts:
            return 0.0, {"required_matched": [], "preferred_matched": [], "score": 0.0, "note": "No fallback context available"}

        fallback_matched = []
        for skill in candidate_skills:
            sim, best = semantic_matcher.calculate_max_similarity(skill, fallback_contexts)
            if sim >= 0.60:
                fallback_matched.append(f"{skill} ({sim:.2f})")

        # Cap lebih rendah (10.0) karena fallback kurang reliable dibanding explicit skill match.
        # 3 skill relevan sudah cukup untuk poin maksimal.
        score = min(10.0, len(fallback_matched) * 3.33)
        return score, {
            "required_matched": fallback_matched,
            "preferred_matched": [],
            "candidate_skills_count": len(candidate_skills),
            "score": round(score, 1),
            "note": "Smart Fallback used (enriched context)",
            "fallback_contexts": fallback_contexts,
        }

    # Match required skills (string first, then semantic fallback)
    req_matched = []
    for skill in required_skills:
        if check_skill_matches(skill, candidate_skills):
            req_matched.append(skill)
        elif _match_skill_semantic(skill, candidate_skills, threshold=settings.SIMILARITY_THRESHOLD_REQUIRED):
            req_matched.append(f"{skill} (semantic)")
            logger.info("Skill [SEMANTIC] '%s' cocok via embedding (bukan exact match)", skill)

    # Match preferred skills
    pref_matched = []
    for skill in preferred_skills:
        if check_skill_matches(skill, candidate_skills):
            pref_matched.append(skill)
        elif _match_skill_semantic(skill, candidate_skills, threshold=settings.SIMILARITY_THRESHOLD_PREFERRED):
            pref_matched.append(f"{skill} (semantic)")
            logger.info("Skill preferred [SEMANTIC] '%s' cocok via embedding", skill)

    # ── Fallback: Cocokkan skill yang belum match terhadap teks jobdesk ──
    # Hanya berjalan jika ada skill yang belum ter-match dan kandidat punya jobdesk.
    # Threshold lebih ketat (0.72) karena jobdesk adalah free text, bukan structured skill.
    JOBDESK_SIM_THRESHOLD = 0.72
    req_matched_names = {m.split(" (")[0].lower() for m in req_matched}
    pref_matched_names = {m.split(" (")[0].lower() for m in pref_matched}

    unmatched_req = [s for s in required_skills if s.lower() not in req_matched_names]
    unmatched_pref = [s for s in preferred_skills if s.lower() not in pref_matched_names]

    if unmatched_req or unmatched_pref:
        from core.utils.skill_helper import build_candidate_jobdesk_texts
        jobdesk_texts = build_candidate_jobdesk_texts(candidate)

        if jobdesk_texts:
            jobdesk_combined_lower = " ".join(jobdesk_texts).lower()

            for skill in unmatched_req:
                skill_lower = normalize_skill(skill)
                if not skill_lower:
                    continue
                # 1. Substring match (murah dan presisi tinggi)
                if skill_lower in jobdesk_combined_lower:
                    req_matched.append(f"{skill} (jobdesk)")
                    logger.info("Skill required [JOBDESK-SUBSTR] '%s' ditemukan dalam teks jobdesk", skill)
                    continue
                # 2. Semantic fallback (threshold ketat)
                sim, _ = semantic_matcher.calculate_max_similarity(skill, jobdesk_texts)
                if sim >= JOBDESK_SIM_THRESHOLD:
                    req_matched.append(f"{skill} (jobdesk)")
                    logger.info("Skill required [JOBDESK-SEMANTIC] '%s' cocok via jobdesk (sim=%.2f)", skill, sim)

            for skill in unmatched_pref:
                skill_lower = normalize_skill(skill)
                if not skill_lower:
                    continue
                if skill_lower in jobdesk_combined_lower:
                    pref_matched.append(f"{skill} (jobdesk)")
                    logger.info("Skill preferred [JOBDESK-SUBSTR] '%s' ditemukan dalam teks jobdesk", skill)
                    continue
                sim, _ = semantic_matcher.calculate_max_similarity(skill, jobdesk_texts)
                if sim >= JOBDESK_SIM_THRESHOLD:
                    pref_matched.append(f"{skill} (jobdesk)")
                    logger.info("Skill preferred [JOBDESK-SEMANTIC] '%s' cocok via jobdesk (sim=%.2f)", skill, sim)

    # Scoring: 9 poin untuk required (proporsional), 6 poin untuk preferred
    req_score = 0.0
    if required_skills:
        req_ratio = len(req_matched) / len(required_skills)
        req_score = req_ratio * 9.0
    else:
        req_score = 5.0  # Tidak ada required -> baseline
        
    pref_score = 0.0
    if preferred_skills:
        pref_score = min(6.0, len(pref_matched) * 3.0)
        
    score = min(15.0, req_score + pref_score)

    return score, {
        "required_matched": req_matched,
        "preferred_matched": pref_matched,
        "candidate_skills_count": len(candidate_skills),
        "score": round(score, 1),
    }


def _score_jobdesk_relevance(candidate, requirements: dict, job_title: str = "") -> tuple[float, dict]:
    """
    Menghitung skor relevansi semantik jobdesk pengalaman kerja dengan requirements (maksimal 15.0).

    Parameter:
        candidate (Require): Objek kandidat dari database.
        requirements (dict): Persyaratan lowongan pekerjaan.
        job_title (str): Judul posisi pekerjaan.

    Return:
        Tuple[float, dict]: Skor relevansi jobdesk dan detail penjelasannya.
    """
    work_experiences = getattr(candidate, "work_experiences", []) or []

    jobdesk_texts = []
    for exp in work_experiences:
        jobdesk = getattr(exp, "jobdesk", None)
        if jobdesk and jobdesk.strip():
            jobdesk_texts.append(jobdesk.strip())

    if not jobdesk_texts:
        return 0.0, {"score": 0.0}

    # Build job context dari skills
    job_context_parts = []
    for skill in requirements.get("required_skills", []):
        job_context_parts.append(skill)
    for skill in requirements.get("preferred_skills", []):
        job_context_parts.append(skill)

    if not job_context_parts:
        if job_title:
            job_context = job_title
        else:
            return 0.0, {"score": 0.0, "note": "No skills context for matching"}
    else:
        job_context = ", ".join(job_context_parts)

    # Find best jobdesk match
    best_sim = 0.0
    for text in jobdesk_texts:
        sim, _ = semantic_matcher.calculate_max_similarity(text, [job_context])
        if sim > best_sim:
            best_sim = sim

    score = min(15.0, best_sim * 18.75) # ~0.80 sim -> 15 pts

    return round(score, 1), {
        "best_similarity": round(best_sim, 3),
        "score": round(score, 1),
    }


def _score_available_soon(candidate) -> tuple[float, dict]:
    """
    Menghitung skor bonus untuk ketersediaan bergabung segera (maksimal 3.0).

    Parameter:
        candidate (Require): Objek kandidat dari database.

    Return:
        Tuple[float, dict]: Skor bonus ketersediaan segera dan detail penjelasannya.
    """
    avail = getattr(candidate, "q16_available_from", None)
    if not avail:
        return 0.0, {"value": None, "score": 0.0}
    
    avail_lower = str(avail).lower().strip()
    immediately_keywords = [
        "immediately", "segera", "now", "asap", "1 week", "2 weeks",
        "1 minggu", "2 minggu", "7 hari", "14 hari", "30 hari", "30 days",
        "1 month", "1 bulan", "1-bulan", "1-month"
    ]
    
    for kw in immediately_keywords:
        if kw in avail_lower:
            return 3.0, {"value": avail, "score": 3.0}
            
    import re
    from datetime import datetime
    date_match = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", avail_lower)
    if date_match:
        try:
            year, month, day = map(int, date_match.groups())
            target_date = datetime(year, month, day)
            delta = (target_date - datetime.now()).days
            if delta <= 30:
                return 3.0, {"value": avail, "score": 3.0}
        except Exception:
            pass
            
    return 0.0, {"value": avail, "score": 0.0}


def _score_income_fit(candidate, requirements: dict) -> tuple[float, dict]:
    """
    Menghitung skor bonus untuk kesesuaian ekspektasi gaji kandidat (maksimal 2.0).

    Parameter:
        candidate (Require): Objek kandidat dari database.
        requirements (dict): Persyaratan pekerjaan dari lowongan.

    Return:
        Tuple[float, dict]: Skor bonus kesesuaian gaji dan detail penjelasannya.
    """
    expected = getattr(candidate, "q15_expected_income", None)
    budget = requirements.get("budget")
    
    if expected is None or budget is None:
        return 0.0, {"expected": expected, "budget": budget, "score": 0.0}
        
    try:
        expected_val = float(expected)
        budget_val = float(budget)
        if expected_val <= budget_val:
            return 2.0, {"expected": expected_val, "budget": budget_val, "score": 2.0}
    except (ValueError, TypeError):
        pass
        
    return 0.0, {"expected": expected, "budget": budget, "score": 0.0}


def _score_industry_relevance(candidate) -> tuple[float, dict]:
    """
    Menghitung skor bonus untuk relevansi industri properti / konstruksi (maksimal 5.0).

    Parameter:
        candidate (Require): Objek kandidat dari database.

    Return:
        Tuple[float, dict]: Skor bonus industri dan detail penjelasannya.
    """
    PROPERTY_COMPANY_KEYWORDS = [
        "developer", "property", "properti", "realty", "real estate",
        "perumahan", "konstruksi", "kontraktor", "land", "estate",
        "ciputra", "agung podomoro", "sinar mas", "summarecon",
        "pakuwon", "lippo", "bsd", "metland", "intiland"
    ]
    
    work_experiences = getattr(candidate, "work_experiences", []) or []
    matches = 0
    for exp in work_experiences:
        company = (getattr(exp, "companyname", "") or "").lower()
        if any(kw in company for kw in PROPERTY_COMPANY_KEYWORDS):
            matches += 1
    
    score = min(5.0, matches * 2.5)
    return score, {"industry_matches": matches, "score": score}


def calculate_candidate_score(candidate, requirements: dict, taxonomy_result: dict, job_title: str = "") -> tuple[float, dict]:
    """
    Menghitung total skor kandidat berdasarkan kecocokan taksonomi, pengalaman, pendidikan,
    jurusan, nilai IPK, sertifikasi, keahlian, jobdesk, serta bonus lainnya.

    Parameter:
        candidate (Require): Objek kandidat dari database.
        requirements (dict): Persyaratan pekerjaan dari lowongan.
        taxonomy_result (dict): Hasil pencocokan taksonomi peran.
        job_title (str): Judul lowongan pekerjaan.

    Return:
        Tuple[float, dict]: Total skor akhir kandidat (maksimal 100.0) dan rincian per komponen.
    """
    breakdown = {}
    
    # Ambil batas minimum pengalaman kerja dari lowongan
    min_exp_req = requirements.get("min_experience_years", 0)
    try:
        min_exp_req = float(min_exp_req) if min_exp_req is not None else 0.0
    except (ValueError, TypeError):
        min_exp_req = 0.0

    # Bobot adaptif fresh graduate hanya diaktifkan untuk lowongan entry-level (<= 1.0 tahun syarat pengalaman)
    is_cand_fg = getattr(candidate, "is_fresh_graduate", False) or False
    is_fresh_grad = is_cand_fg and (min_exp_req <= 1.0)

    # Hitung skor komponen utama
    tax_score, tax_detail = _score_taxonomy(taxonomy_result)
    skills_score, skills_detail = _score_skills_match(candidate, requirements, job_title)

    # Hitung rasio kecocokan keahlian wajib
    required_skills = requirements.get("required_skills", [])
    if required_skills:
        req_matched = skills_detail.get("required_matched", [])
        skills_match_pct = len(req_matched) / len(required_skills)
    else:
        skills_match_pct = 1.0

    exp_score, exp_detail = _score_experience_surplus(requirements, taxonomy_result, skills_match_pct)
    edu_score, edu_detail = _score_education_surplus(candidate, requirements)
    major_score, major_detail = _score_major_match(candidate, requirements)
    gpa_score, gpa_detail = _score_gpa(candidate)
    cert_score, cert_detail = _score_certifications(candidate, requirements)
    jobdesk_score, jobdesk_detail = _score_jobdesk_relevance(candidate, requirements, job_title)
    
    # Hitung bonus tambahan
    avail_score, avail_detail = _score_available_soon(candidate)
    income_score, income_detail = _score_income_fit(candidate, requirements)

    # Bonus industri property hanya aktif jika di-enable via konfigurasi
    if settings.ENABLE_INDUSTRY_BONUS:
        ind_score, ind_detail = _score_industry_relevance(candidate)
    else:
        ind_score, ind_detail = 0.0, {"industry_matches": 0, "score": 0.0, "note": "disabled"}

    # Bobot adaptif fresh graduate vs profesional
    if is_fresh_grad:
        total = (
            tax_score * 0.60 +      # Taksonomi kurang relevan untuk FG
            exp_score * 0.10 +      # Pengalaman minimal untuk FG
            edu_score * 1.80 +      # Pendidikan ditingkatkan
            major_score * 1.50 +     # Jurusan ditingkatkan
            gpa_score * 2.40 +       # IPK sangat penting
            cert_score * 1.20 +      # Sertifikasi ditingkatkan
            skills_score * 1.80 +    # Keahlian ditingkatkan
            jobdesk_score * 0.00     # Jobdesk tidak dihitung untuk FG
        )
        breakdown["fresh_graduate"] = True
    else:
        total = (
            tax_score +
            exp_score +
            edu_score +
            major_score +
            gpa_score +
            cert_score +
            skills_score +
            jobdesk_score
        )
        breakdown["fresh_graduate"] = False
        
    # Tambahkan bonus secara mutlak (tidak terpengaruh pengali fresh grad)
    total += avail_score
    total += income_score
    total += ind_score

    # Rincian breakdown
    breakdown["taxonomy_match"] = tax_detail
    breakdown["experience_surplus"] = exp_detail
    breakdown["education_surplus"] = edu_detail
    breakdown["major_match"] = major_detail
    breakdown["gpa_score"] = gpa_detail
    breakdown["certifications"] = cert_detail
    breakdown["skills_match"] = skills_detail
    breakdown["jobdesk_relevance"] = jobdesk_detail
    breakdown["available_soon"] = avail_detail
    breakdown["income_fit"] = income_detail
    breakdown["industry_relevance"] = ind_detail
    # Cap skor untuk non-relevant matches (kecuali fresh graduate)
    match_type = taxonomy_result.get("match_type", "unrelated")
    if match_type in ("unknown", "unrelated", "no_experience") and not is_fresh_grad:
        total = min(total, 25.0)
    # Batasi total skor maksimal di angka 100.0 secara global
    total = min(100.0, total)

    # Deteksi profil tidak lengkap (kandidat belum diekstrak tagnya)
    # Jika candidate_tags None, berarti belum diproses oleh candidate_tagger
    if not getattr(candidate, "candidate_tags", None):
        total = round(total * 0.70, 1)  # Pinalti moderat — data structured tetap dihargai
        breakdown["incomplete_profile"] = True
        breakdown["score_cap"] = {"applied": True, "reason": "Data profil kurang lengkap (tag belum diekstrak)"}

    return round(total, 1), breakdown
