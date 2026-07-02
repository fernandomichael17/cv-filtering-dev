"""Kebijakan penapisan untuk kandidat profesional."""

from core.filtering.taxonomy.experience_evaluator import _check_major_relevance

def _make_professional_decision(
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
    is_general_program: bool,
    max_experience_years: float | None,
    min_experience_years: float,
    candidate_educations: list | None,
) -> dict:
    """Mengambil keputusan kelayakan untuk kandidat professional berdasarkan hasil evaluasi.

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
        is_general_program (bool): Status program umum (Trainee/MT).
        max_experience_years (float | None): Batas maksimum pengalaman kerja.
        min_experience_years (float): Batas minimum pengalaman kerja.
        candidate_educations (list | None): Riwayat pendidikan kandidat.

    Return:
        dict: Hasil evaluasi akhir berupa keputusan dan alasan.
    """
    # Pengecekan pencabangan switch/match deklaratif berdasarkan tipe kecocokan (best_match_type)
    if best_match_type in ("exact", "related"):
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
        if relevant_years >= min_experience_years:
            return {
                "decision": "PASS",
                "match_type": best_match_type,
                "job_node": job_code,
                "candidate_nodes": candidate_codes,
                "relevant_years": round(relevant_years, 1),
                "total_years": round(total_years, 1),
                "reason": (
                    f"Pengalaman kandidat sebagai {roles_str} ({relevant_years:.1f} thn relevan) "
                    f"memenuhi syarat minimum {min_experience_years} tahun untuk posisi {job_title}."
                ),
            }
        else:
            # Di mode relaxed, jika best_match_type adalah related (serumpun)
            # dan total masa kerja aktif kandidat masih memenuhi min_experience_years,
            # alihkan ke status UNKNOWN (REVIEW) alih-alih langsung dieliminasi secara mutlak.
            if relaxed and best_match_type == "related" and total_years >= min_experience_years:
                return {
                    "decision": "UNKNOWN",
                    "match_type": best_match_type,
                    "job_node": job_code,
                    "candidate_nodes": candidate_codes,
                    "relevant_years": round(relevant_years, 1),
                    "total_years": round(total_years, 1),
                    "reason": (
                        f"Pengalaman kandidat sebagai {roles_str} bertipe serumpun (related) dengan "
                        f"total masa kerja {total_years:.1f} tahun, namun relevansi parsial ({relevant_years:.1f} tahun) "
                        f"di bawah minimum {min_experience_years:.1f} tahun. Diloloskan ke REVIEW untuk ditinjau manual."
                    ),
                }
            return {
                "decision": "FAIL",
                "match_type": best_match_type,
                "job_node": job_code,
                "candidate_nodes": candidate_codes,
                "relevant_years": round(relevant_years, 1),
                "total_years": round(total_years, 1),
                "reason": (
                    f"[Masa Kerja] Pengalaman relevan sebagai {roles_str} hanya {relevant_years:.1f} tahun, "
                    f"kurang dari minimum {min_experience_years:.1f} tahun untuk posisi {job_title}."
                ),
            }

    if best_match_type == "loosely_related":
        has_relevant_major = _check_major_relevance(candidate_educations, job_title, job_tags)
        if has_skills_match or has_relevant_major or relaxed:
            exp_to_check = total_years if is_general_program else relevant_years
            if max_experience_years is not None and exp_to_check > max_experience_years:
                return {
                    "decision": "FAIL",
                    "match_type": best_match_type,
                    "job_node": job_code,
                    "candidate_nodes": candidate_codes,
                    "relevant_years": 0,
                    "total_years": round(total_years, 1),
                    "reason": (
                        f"Total pengalaman kerja ({total_years:.1f} tahun) melebihi batas maksimum {max_experience_years} tahun untuk program trainee/MT."
                        if is_general_program else
                        f"Pengalaman relevan sebagai {roles_str} (0.0 tahun) melebihi batas maksimum {max_experience_years} tahun untuk posisi {job_title}."
                    ),
                }
            return {
                "decision": "UNKNOWN",
                "match_type": best_match_type,
                "job_node": job_code,
                "candidate_nodes": candidate_codes,
                "relevant_years": 0,
                "total_years": round(total_years, 1),
                "reason": (
                    f"Pengalaman kandidat sebagai {roles_str} memiliki Relevansi Sebagian (Partially Relevant) diloloskan di mode relaxed untuk review manual."
                    if relaxed else
                    f"Pengalaman kandidat sebagai {roles_str} memiliki tingkat Relevansi Sebagian (Partially Relevant) terhadap posisi {job_title}, namun diloloskan ke UNKNOWN "
                    f"karena memiliki kesesuaian skill/jurusan untuk review manual."
                ),
            }
        else:
            return {
                "decision": "FAIL",
                "match_type": best_match_type,
                "job_node": job_code,
                "candidate_nodes": candidate_codes,
                "relevant_years": 0,
                "total_years": round(total_years, 1),
                "reason": (
                    f"[Kesesuaian Posisi] Pengalaman kerja kandidat sebagai {roles_str} dikategorikan memiliki Relevansi Sebagian (Partially Relevant) "
                    f"dan tidak memiliki kesesuaian keahlian spesifik atau latar belakang jurusan yang relevan untuk posisi {job_title}."
                ),
            }

    if best_match_type == "unknown":
        return {
            "decision": "UNKNOWN",
            "match_type": best_match_type,
            "job_node": job_code,
            "candidate_nodes": candidate_codes,
            "relevant_years": 0,
            "total_years": round(total_years, 1),
            "reason": (
                f"Pengalaman kandidat sebagai {roles_str} memiliki tingkat relevansi "
                f"yang abu-abu ({best_match_type.replace('_', ' ')}) terhadap posisi {job_title}. "
                f"Diloloskan untuk direview lebih lanjut."
            ),
        }

    if best_match_type == "unrelated":
        has_relevant_major = _check_major_relevance(candidate_educations, job_title, job_tags)
        if has_skills_match and (has_relevant_major or relaxed):
            return {
                "decision": "UNKNOWN",
                "match_type": "unrelated",
                "job_node": job_code,
                "candidate_nodes": candidate_codes,
                "relevant_years": 0,
                "total_years": round(total_years, 1),
                "reason": (
                    f"Meskipun bidang pengalaman kandidat ({roles_str}) tidak relevan, kandidat diloloskan di mode relaxed karena memiliki kesesuaian skill ({skills_str})."
                    if relaxed else
                    f"Meskipun bidang pengalaman kandidat ({roles_str}) bertipe tidak relevan (unrelated) "
                    f"terhadap posisi {job_title}, kandidat diloloskan ke UNKNOWN karena memiliki "
                    f"kesesuaian skill ({skills_str}) dan jurusan yang relevan untuk ditinjau manual."
                ),
            }

    return {
        "decision": "FAIL",
        "match_type": "unrelated",
        "job_node": job_code,
        "candidate_nodes": candidate_codes,
        "relevant_years": 0,
        "total_years": round(total_years, 1),
        "reason": (
            f"[Kesesuaian Posisi] Bidang pengalaman kerja kandidat ({roles_str}) "
            f"tidak relevan dengan posisi yang dicari ({job_title})."
        ),
    }

