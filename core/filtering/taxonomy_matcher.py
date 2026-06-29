"""Layer 2 — Taxonomy-Based Job Role Matching (ISCO-08 / KBJI) - Facade (P16).

Merupakan pintu masuk utama (facade) untuk seluruh penyaringan berbasis taksonomi pekerjaan.
Mengimpor fungsionalitas dari sub-modul terpisah di bawah package `core.filtering.taxonomy`
dan mengekspor fungsi-fungsi utama untuk menjamin kompatibilitas ke belakang (backward compatibility).
"""

import logging
from core.filtering.taxonomy.decision_engine import (
    apply_taxonomy_filter,
    _match_job_role_impl,
)
from core.filtering.taxonomy.skills_evaluator import _check_skills_match
from core.filtering.taxonomy.experience_evaluator import (
    _calc_experience_months,
    _extract_role_from_tags,
)
from core.filtering.taxonomy.field_compatibility import get_match_type

logger = logging.getLogger(__name__)


def _match_job_role_orig(
    candidate_experiences: list,
    job_title: str,
    min_experience_years: float,
    cv_tags_str: str | None = None,
    job_tags: list[str] | None = None,
    candidate_educations: list | None = None,
    max_experience_years: float | None = None,
    is_fresh_graduate: bool = False,
    relaxed: bool = False,
) -> dict:
    """Wrapper untuk mengevaluasi kecocokan taksonomi dan menyisipkan hasil skills match.

    Parameter:
        candidate_experiences (list): Daftar riwayat pengalaman kerja kandidat.
        job_title (str): Judul posisi pekerjaan yang ditargetkan.
        min_experience_years (float): Batas minimum pengalaman kerja yang dibutuhkan.
        cv_tags_str (str | None): Tag keahlian kandidat.
        job_tags (list[str] | None): Kumpulan tag lowongan pekerjaan.
        candidate_educations (list | None): Riwayat pendidikan kandidat.
        max_experience_years (float | None): Batas maksimum pengalaman kerja yang diperbolehkan.
        is_fresh_graduate (bool): Status fresh graduate kandidat.
        relaxed (bool): Mengaktifkan pencocokan toleransi tinggi (Tier 2).

    Return:
        dict: Hasil evaluasi taksonomi yang telah dilengkapi dengan has_skills_match.
    """
    has_skills_match, matched_skills = _check_skills_match(cv_tags_str, candidate_experiences, job_tags)
    unique_matched_skills = list(dict.fromkeys(matched_skills))
    skills_str = ", ".join(unique_matched_skills) if unique_matched_skills else ""

    result = _match_job_role_impl(
        candidate_experiences,
        job_title,
        min_experience_years,
        cv_tags_str,
        job_tags,
        candidate_educations,
        max_experience_years,
        is_fresh_graduate,
        relaxed,
        has_skills_match,
        skills_str,
    )
    result["has_skills_match"] = has_skills_match
    return result


def match_job_role(
    candidate_experiences: list,
    job_title: str,
    min_experience_years: float,
    cv_tags_str: str | None = None,
    job_tags: list[str] | None = None,
    candidate_educations: list | None = None,
    max_experience_years: float | None = None,
    is_fresh_graduate: bool = False,
    relaxed: bool = False,
) -> dict:
    """Eksport resmi match_job_role yang melakukan pencegahan job hopping.

    Parameter:
        candidate_experiences (list): Daftar riwayat pengalaman kerja kandidat.
        job_title (str): Judul posisi pekerjaan yang ditargetkan.
        min_experience_years (float): Batas minimum pengalaman kerja yang dibutuhkan.
        cv_tags_str (str | None): Tag keahlian kandidat.
        job_tags (list[str] | None): Kumpulan tag lowongan pekerjaan.
        candidate_educations (list | None): Riwayat pendidikan kandidat.
        max_experience_years (float | None): Batas maksimum pengalaman kerja yang diperbolehkan.
        is_fresh_graduate (bool): Status fresh graduate kandidat.
        relaxed (bool): Mengaktifkan pencocokan toleransi tinggi (Tier 2).

    Return:
        dict: Hasil pencocokan taksonomi yang telah dievaluasi.
    """
    result = _match_job_role_orig(
        candidate_experiences,
        job_title,
        min_experience_years,
        cv_tags_str,
        job_tags,
        candidate_educations,
        max_experience_years,
        is_fresh_graduate,
        relaxed
    )

    # Intercept untuk aturan Job Hopping (TC-16):
    # Kandidat terdeteksi sebagai job hopper jika memiliki > 3 posisi DAN rata-rata durasi
    # per posisi < 12 bulan. Ini mencegah kandidat senior progresif (misal: 4 posisi × 3 tahun)
    # salah diklasifikasi sebagai job hopper.
    if candidate_experiences and len(candidate_experiences) > 3:
        total_duration_months = sum(_calc_experience_months(exp) for exp in candidate_experiences)
        avg_duration_months = total_duration_months / len(candidate_experiences)
        is_job_hopper = avg_duration_months < 12.0

        if is_job_hopper and result.get("decision") == "PASS":
            result["decision"] = "UNKNOWN"
            result["reason"] = (
                f"[Job Hopping] Kandidat terdeteksi sering berpindah tempat kerja "
                f"({len(candidate_experiences)} posisi, rata-rata {avg_duration_months:.0f} bulan/posisi, "
                f"batas minimum rata-rata 12 bulan). "
                f"Keputusan diturunkan dari PASS menjadi REVIEW untuk ditinjau manual."
            )

        # Lakukan hal yang sama untuk hasil relaxed (Tier 2) jika ada
        if is_job_hopper:
            relaxed_res = result.get("relaxed_result")
            if relaxed_res and relaxed_res.get("decision") == "PASS":
                relaxed_res["decision"] = "UNKNOWN"
                relaxed_res["reason"] = (
                    f"[Job Hopping] Kandidat terdeteksi sering berpindah tempat kerja "
                    f"({len(candidate_experiences)} posisi, rata-rata {avg_duration_months:.0f} bulan/posisi, "
                    f"batas minimum rata-rata 12 bulan). "
                    f"Keputusan diturunkan dari PASS menjadi REVIEW untuk ditinjau manual."
                )

    return result
