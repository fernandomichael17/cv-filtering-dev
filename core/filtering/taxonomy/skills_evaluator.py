"""Modul Evaluasi dan Pencocokan Keahlian (Skills Matching) (P16)."""

import logging
from app.config import settings
from core.filtering.semantic_matcher import semantic_matcher
from core.filtering.taxonomy.field_compatibility import BROAD_CATEGORIES

logger = logging.getLogger(__name__)

def _build_dynamic_skill_profile(
    cv_tags_str: str | None,
    candidate_experiences: list,
) -> list[str]:
    """Dynamically construct a candidate's skill profile from ground-truth data.

    Sources (in order):
    1. cv_tags_str (candidate_tags.tags — backward compat format)
    2. work_experiences.experience_tags.tags ("bidang, jabatan" per experience)

    Returns:
        Deduplicated list of lowercase skill/tag strings.
    """
    seen: set[str] = set()
    result: list[str] = []

    def _add(tag: str) -> None:
        tag = tag.strip().lower()
        if tag and tag not in seen:
            seen.add(tag)
            result.append(tag)

    # Source 1: CV tags (candidate_tags table)
    if cv_tags_str:
        for t in cv_tags_str.split(","):
            _add(t)

    # Source 2: Work experience tags (candidate_experience_tags table)
    for exp in candidate_experiences or []:
        exp_tags_obj = getattr(exp, "experience_tags", None)
        if exp_tags_obj:
            tags_str = getattr(exp_tags_obj, "tags", None)
            if tags_str:
                for t in tags_str.split(","):
                    _add(t)

    return result




def _check_skills_match(
    cv_tags_str: str | None,
    candidate_experiences: list,
    job_tags: list[str] | None
) -> tuple[bool, list[str]]:
    """Mengevaluasi kecocokan keahlian (skills match) kandidat dengan lowongan.

    Mengabaikan kategori besar (BROAD_CATEGORIES) dan mencocokkan tag spesifik.

    Parameter:
        cv_tags_str (str | None): Tag keahlian kandidat.
        candidate_experiences (list): Pengalaman kerja kandidat.
        job_tags (list[str] | None): Kumpulan tag pekerjaan.

    Return:
        Tuple[bool, list[str]]: Status kecocokan dan list tag keahlian yang cocok.
    """
    cv_tags = _build_dynamic_skill_profile(cv_tags_str, candidate_experiences)
    job_tags_clean = [t.strip().lower() for t in job_tags if t.strip()] if job_tags else []
    specific_job_tags = job_tags_clean[1:] if len(job_tags_clean) > 1 else job_tags_clean

    cv_tags_specific = [t.strip().lower() for t in cv_tags if t.strip().lower() not in BROAD_CATEGORIES]

    has_skills_match = False
    matched_skills = []
    if cv_tags_specific and specific_job_tags:
        for c_tag in cv_tags_specific:
            for j_tag in specific_job_tags:
                if c_tag == j_tag or c_tag in j_tag or j_tag in c_tag:
                    has_skills_match = True
                    matched_skills.append(c_tag)
                    break
        
        if not has_skills_match:
            for c_tag in cv_tags_specific:
                for j_tag in specific_job_tags:
                    sim_score, _ = semantic_matcher.calculate_max_similarity(c_tag, [j_tag])
                    if sim_score >= settings.SIMILARITY_THRESHOLD_TAXONOMY_SKILLS:
                        has_skills_match = True
                        matched_skills.append(c_tag)
                        break
                        
    return has_skills_match, matched_skills



