"""Skills-based soft filter — Layer 1.7.

Rejects candidates who have ZERO overlap between their skills
and the job's required_skills. This is a quick deterministic check
using string matching + semantic fallback.

Only applied when required_skills is present in the JD.
Candidates with no detectable skills are passed through (benefit of the doubt).
"""

import logging

from app.config import settings
from core.filtering.semantic_matcher import semantic_matcher
from core.utils.skill_synonyms import normalize_skill, are_skills_similar
from core.utils.skill_helper import build_candidate_skills, check_skill_matches
from core.filtering.hard_filter import (
    _get_highest_education,
)

logger = logging.getLogger(__name__)


# Catatan: _build_candidate_skills dipindahkan ke core.utils.skill_helper.py untuk mengeliminasi duplikasi.





def _has_related_major(candidate, allowed_majors: list[str]) -> bool:
    """Check if the candidate has a major related to the job requirements."""
    if not allowed_majors:
        return True

    educations = getattr(candidate, "educations", []) or []
    _, _, major, _ = _get_highest_education(educations)
    
    from core.utils.major_matcher import check_major_match
    return check_major_match(major, allowed_majors)


def apply_skills_filter(
    candidates: list,
    requirements: dict,
    min_match_ratio: float = 0.5,
    taxonomy_results: dict | None = None,
) -> tuple[list, list[dict]]:
    """
    Menerapkan penyaringan berbasis keahlian (skills-based filter) terhadap kandidat.

    Kandidat harus memiliki minimal satu kecocokan keahlian wajib. Jika min_match_ratio > 0,
    kandidat harus memenuhi rasio kecocokan keahlian wajib tertentu sesuai nilai ambang batas.
    Kandidat dengan kecocokan taksonomi peran yang kuat (exact atau related) akan langsung
    diloloskan untuk dievaluasi pada tahap penilaian (scoring).

    Parameter:
        candidates (list): Daftar kandidat (objek Require ORM) yang dimuat dari database.
        requirements (dict): Persyaratan pekerjaan terstruktur hasil ekstraksi LLM.
        min_match_ratio (float): Rasio minimum kecocokan keahlian wajib yang disyaratkan.
        taxonomy_results (dict, opsional): Hasil pencocokan taksonomi peran kandidat dari Layer 2.

    Return:
        Tuple[list, list[dict]]: Pasangan daftar kandidat yang lolos (passed) dan daftar kandidat yang tereliminasi (eliminated).
    """
    required_skills = requirements.get("required_skills", [])

    # Skip if no required skills defined
    if not required_skills:
        logger.info("Skills filter skipped (no required_skills in JD)")
        return candidates, []

    allowed_majors = requirements.get("allowed_majors", [])
    if isinstance(allowed_majors, str):
        allowed_majors = [m.strip() for m in allowed_majors.split(",") if m.strip()]

    passed = []
    eliminated = []

    for candidate in candidates:
        name = f"{candidate.firstname or ''} {candidate.lastname or ''}".strip()
        rid = candidate.requireid
        is_fresh_grad = getattr(candidate, "is_fresh_graduate", False) or False

        # Ambil tipe kecocokan taksonomi kandidat untuk pengecualian filter keahlian
        tax_res = taxonomy_results.get(rid) if taxonomy_results else None
        tax_match = tax_res.get("match_type", "unrelated") if tax_res else "unrelated"

        candidate_skills = build_candidate_skills(candidate)
        has_rel_major = _has_related_major(candidate, allowed_majors)

        # Handle candidates with no detectable skills at all
        if not candidate_skills:
            if is_fresh_grad and has_rel_major:
                passed.append(candidate)
                continue
            else:
                reason_detail = (
                    "Kandidat tidak memiliki data keahlian (skills) di CV untuk mencocokkan required skills"
                    if has_rel_major
                    else "Kandidat dari jurusan tidak sejenis tidak memiliki data keahlian (skills) di CV untuk mencocokkan required skills"
                )
                eliminated.append({
                    "require_id": rid,
                    "candidate_name": name,
                    "reason": f"[Keahlian] {reason_detail}: {', '.join(required_skills)}."
                })
                continue

        # Count matches for required skills (separate hard vs semantic/similar)
        matched_required_hard = []
        matched_required_semantic = []
        for skill in required_skills:
            if check_skill_matches(skill, candidate_skills):
                matched_required_hard.append(skill)
            else:
                # 1. Pengecekan Skill Sejenis/Mirip (Skill Cluster fallback)
                similar_found = False
                for cs in candidate_skills:
                    if are_skills_similar(skill, cs):
                        matched_required_semantic.append(f"{skill} (similar: {cs})")
                        similar_found = True
                        break
                
                # 2. Semantic fallback standard
                if not similar_found:
                    sim, _ = semantic_matcher.calculate_max_similarity(skill, list(candidate_skills))
                    if sim >= settings.SIMILARITY_THRESHOLD_REQUIRED:
                        matched_required_semantic.append(skill)

        # Combine matches for ratio/threshold checks
        matched_required = [f"{s} (hard)" for s in matched_required_hard] + [f"{s} (semantic)" for s in matched_required_semantic]

        # For candidates with unrelated majors, they MUST match at least one required skill (regardless of fresh grad status)
        if not has_rel_major:
            if len(matched_required_hard) == 0 and len(matched_required_semantic) == 0:
                eliminated.append({
                    "require_id": rid,
                    "candidate_name": name,
                    "reason": (
                        f"[Keahlian] Latar belakang jurusan kandidat tidak sejenis dan tidak memiliki satu pun keahlian wajib yang disyaratkan. "
                        f"Wajib: {', '.join(required_skills)}. "
                        f"Keahlian kandidat: {', '.join(sorted(candidate_skills)[:5])}{'...' if len(candidate_skills) > 5 else ''}."
                    ),
                })
                continue

        # Count matches for preferred skills (from JD)
        preferred_skills = requirements.get("preferred_skills", [])
        matched_preferred = []
        for skill in preferred_skills:
            if check_skill_matches(skill, candidate_skills):
                matched_preferred.append(skill)
            else:
                # Semantic fallback
                sim, _ = semantic_matcher.calculate_max_similarity(skill, list(candidate_skills))
                if sim >= settings.SIMILARITY_THRESHOLD_PREFERRED:
                    matched_preferred.append(f"{skill} (semantic)")

        # ── SAFETY GUARD HARD REJECT ──────────────────────────────────────────
        # Non-fresh grads MUST match at least one required skill if required_skills count >= 2
        # (Exempt if required_skills < 2 to prevent single point of failure in JD parser)
        if not is_fresh_grad and required_skills and len(required_skills) >= 2:
            if len(matched_required_hard) == 0 and len(matched_required_semantic) == 0:
                eliminated.append({
                    "require_id": rid,
                    "candidate_name": name,
                    "reason": (
                        f"[Keahlian] Kandidat tidak memiliki keahlian wajib yang disyaratkan lowongan. "
                        f"Wajib: {', '.join(required_skills)}. "
                        f"Keahlian kandidat: {', '.join(sorted(candidate_skills)[:5])}{'...' if len(candidate_skills) > 5 else ''}."
                    ),
                })
                continue
        # ──────────────────────────────────────────────────────────────────────

        total_matched = len(matched_required) + len(matched_preferred)
        match_ratio = len(matched_required) / len(required_skills) if required_skills else 1.0

        # Fresh graduates get a more lenient threshold for ratio
        effective_threshold = min_match_ratio
        if is_fresh_grad:
            effective_threshold = 0.0  # Fresh grads: any single match is enough

        # Check: at least 1 required or preferred skill must match
        if total_matched == 0:
            eliminated.append({
                "require_id": rid,
                "candidate_name": name,
                "reason": (
                    f"[Keahlian] Tidak ditemukan kecocokan keahlian pada CV kandidat, baik keahlian wajib maupun yang diutamakan. "
                    f"Wajib: {', '.join(required_skills)}. "
                    f"Diutamakan: {', '.join(preferred_skills) if preferred_skills else 'tidak ada'}. "
                    f"Keahlian kandidat: {', '.join(sorted(candidate_skills)[:5])}{'...' if len(candidate_skills) > 5 else ''}."
                ),
            })
            continue

        if match_ratio < effective_threshold and effective_threshold > 0:
            eliminated.append({
                "require_id": rid,
                "candidate_name": name,
                "reason": (
                    f"[Keahlian] Rasio kecocokan keahlian wajib kandidat ({match_ratio:.0%}) di bawah ambang batas minimum yang ditentukan ({effective_threshold:.0%}). "
                    f"Keahlian yang cocok: {', '.join(matched_required) if matched_required else 'tidak ada'}."
                ),
            })
            continue

        passed.append(candidate)

    logger.info(
        "Skills filter: %d passed, %d eliminated out of %d total",
        len(passed), len(eliminated), len(candidates),
    )
    return passed, eliminated
