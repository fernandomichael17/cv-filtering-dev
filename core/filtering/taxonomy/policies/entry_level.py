"""Kebijakan penapisan untuk entry level dan fresh graduate."""

from core.filtering.taxonomy.field_compatibility import _is_bypass_allowed
from core.filtering.taxonomy.experience_evaluator import _check_major_relevance

def _make_entry_level_decision(
    relaxed: bool,
    job_code: str,
    job_title: str,
    job_tags: list[str] | None,
    best_match_type: str,
    relevant_years: float,
    total_years: float,
    candidate_codes: list[str],
    roles_str: str,
    has_skills_match: bool,
    skills_str: str,
    is_fresh_graduate: bool,
    is_general_program: bool,
    max_experience_years: float | None,
    candidate_educations: list | None = None,
    min_experience_years: float = 0.0,
) -> dict:
    """Mengambil keputusan kelayakan untuk kandidat entry-level berdasarkan hasil evaluasi.

    Parameter:
        relaxed (bool): Status penapisan mode longgar.
        job_code (str): Kode taksonomi ISCO lowongan.
        job_title (str): Judul lowongan.
        job_tags (list[str] | None): Tag lowongan.
        best_match_type (str): Tingkat kecocokan terbaik hasil evaluasi.
        relevant_years (float): Total tahun pengalaman relevan.
        total_years (float): Total tahun pengalaman kerja.
        candidate_codes (list[str]): Kode-kode ISCO pengalaman kandidat.
        roles_str (str): Gabungan nama peran pengalaman kandidat.
        has_skills_match (bool): Status kecocokan keahlian.
        skills_str (str): Gabungan nama-nama keahlian cocok.
        is_fresh_graduate (bool): Status fresh graduate kandidat.
        is_general_program (bool): Status program umum (Trainee/MT).
        max_experience_years (float | None): Batas maksimum pengalaman kerja.
        candidate_educations (list | None): Riwayat pendidikan kandidat.
        min_experience_years (float): Batas minimum pengalaman kerja.

    Return:
        dict: Hasil evaluasi akhir berupa keputusan dan alasan.
    """
    # Check max_experience_years limit for general MT program vs specialized role
    exp_to_check = total_years if is_general_program else relevant_years
    if max_experience_years is not None and exp_to_check > max_experience_years:
        return {
            "decision": "FAIL",
            "match_type": best_match_type,
            "job_node": job_code,
            "candidate_nodes": candidate_codes,
            "relevant_years": round(relevant_years, 1),
            "total_years": round(total_years, 1),
            "reason": (
                f"[Masa Kerja] Total pengalaman kerja ({total_years:.1f} tahun) melebihi batas maksimum {max_experience_years:.1f} tahun untuk program trainee/MT."
                if is_general_program else
                f"[Masa Kerja] Pengalaman relevan sebagai {roles_str} ({relevant_years:.1f} tahun) melebihi batas maksimum {max_experience_years:.1f} tahun untuk posisi {job_title}."
            ),
        }

    has_relevant_major = _check_major_relevance(candidate_educations, job_title, job_tags)

    if best_match_type in ("exact", "related"):
        return {
            "decision": "PASS",
            "match_type": best_match_type,
            "job_node": job_code,
            "candidate_nodes": candidate_codes,
            "relevant_years": round(relevant_years, 1),
            "total_years": round(total_years, 1),
            "reason": (
                f"Kandidat diloloskan dengan pengalaman relevan sebagai {roles_str} "
                f"({relevant_years:.1f} tahun) memenuhi syarat lowongan."
            ),
        }
    elif has_skills_match and is_fresh_graduate:
        # Hanya kandidat fresh graduate asli yang boleh bypass ke status PASS
        return {
            "decision": "PASS",
            "match_type": "skills_match",
            "job_node": job_code,
            "candidate_nodes": candidate_codes,
            "relevant_years": 0.0,
            "total_years": round(total_years, 1),
            "reason": (
                f"Fresh graduate diloloskan berbasis kecocokan keahlian CV ({skills_str}) "
                f"meskipun belum memiliki riwayat kerja formal yang relevan."
            ),
        }
    elif is_fresh_graduate and has_relevant_major and min_experience_years == 0.0:
        return {
            "decision": "PASS",
            "match_type": "major_match",
            "job_node": job_code,
            "candidate_nodes": candidate_codes,
            "relevant_years": 0.0,
            "total_years": round(total_years, 1),
            "reason": (
                f"Fresh graduate dengan jurusan relevan diloloskan untuk posisi junior "
                f"'{job_title}' (0 tahun pengalaman kerja)."
            ),
        }
    elif is_fresh_graduate and has_relevant_major:
        return {
            "decision": "UNKNOWN",
            "match_type": "major_match",
            "job_node": job_code,
            "candidate_nodes": candidate_codes,
            "relevant_years": 0.0,
            "total_years": round(total_years, 1),
            "reason": (
                f"Fresh graduate tanpa pengalaman kerja relevan namun memiliki jurusan yang relevan "
                f"diloloskan sebagai UNKNOWN untuk ditinjau manual."
            ),
        }
    else:
        # BYPASS LOGIC: Entry-Level Sales/Admin/General Roles
        if _is_bypass_allowed(job_title):
            return {
                "decision": "PASS",
                "match_type": "loosely_related",
                "job_node": job_code,
                "candidate_nodes": candidate_codes,
                "relevant_years": 0.0,
                "total_years": round(total_years, 1),
                "reason": (
                    f"Bypass Lintas Bidang: Kandidat dengan riwayat '{roles_str}' diloloskan untuk posisi "
                    f"umum '{job_title}' meskipun beda jurusan, karena menerima pelamar lintas bidang."
                ),
            }

        if relaxed and (best_match_type == "loosely_related" or has_skills_match or has_relevant_major):
            return {
                "decision": "UNKNOWN",
                "match_type": "loosely_related" if best_match_type == "loosely_related" else ("skills_match" if has_skills_match else "major_match"),
                "job_node": job_code,
                "candidate_nodes": candidate_codes,
                "relevant_years": 0.0,
                "total_years": round(total_years, 1),
                "reason": f"Diloloskan di mode relaxed sebagai rekomendasi alternatif."
            }

        # Jika bukan fresh graduate dan riwayat kerjanya murni tidak relevan, langsung eliminasi (FAIL)
        return {
            "decision": "FAIL",
            "match_type": "unrelated",
            "job_node": job_code,
            "candidate_nodes": candidate_codes,
            "relevant_years": 0.0,
            "total_years": round(total_years, 1),
            "reason": (
                f"[Kesesuaian Posisi] Riwayat pekerjaan kandidat di bidang lain ({roles_str}) "
                f"tidak relevan dengan posisi yang dicari ({job_title})."
            ),
        }

