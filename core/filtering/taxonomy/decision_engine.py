"""Modul Orkestrasi Keputusan Kelayakan Penyaringan Taksonomi (P16)."""

import logging
from app.config import settings
from core.filtering.isco_normalizer import normalize_to_isco
from core.filtering.taxonomy.field_compatibility import (
    _are_fields_compatible,
    _is_bypass_allowed,
)
from core.filtering.taxonomy.skills_evaluator import _check_skills_match, _build_dynamic_skill_profile
from core.filtering.taxonomy.experience_evaluator import (
    _calc_experience_months,
    _evaluate_all_experiences,
    _is_general_trainee_program,
    _check_major_relevance,
)

logger = logging.getLogger(__name__)

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
                    f"Pengalaman kandidat sebagai {roles_str} bertipe loosely related diloloskan di mode relaxed untuk review manual."
                    if relaxed else
                    f"Pengalaman kandidat sebagai {roles_str} memiliki tingkat relevansi "
                    f"loosely related terhadap posisi {job_title}, namun diloloskan ke UNKNOWN "
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
                    f"[Kesesuaian Posisi] Pengalaman kerja kandidat sebagai {roles_str} dikategorikan kurang relevan (loosely related) "
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




def _match_job_role_impl(
    candidate_experiences: list,
    job_title: str,
    min_experience_years: float,
    cv_tags_str: str | None = None,
    job_tags: list[str] | None = None,
    candidate_educations: list | None = None,
    max_experience_years: float | None = None,
    is_fresh_graduate: bool = False,
    relaxed: bool = False,
    has_skills_match: bool = False,
    skills_str: str = "",
) -> dict:
    """Fungsi internal untuk mengevaluasi kecocokan riwayat pengalaman kerja kandidat

    menggunakan kode taksonomi ISCO dan menangani bypass untuk fresh graduate.

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
        has_skills_match (bool): Status kecocokan keahlian kandidat.
        skills_str (str): String gabungan nama-nama keahlian yang cocok.

    Return:
        dict: Hasil evaluasi taksonomi.
    """
    if min_experience_years is None:
        min_experience_years = 0.0
    else:
        try:
            min_experience_years = float(min_experience_years)
        except (ValueError, TypeError):
            min_experience_years = 0.0

    if max_experience_years is not None:
        try:
            max_experience_years = float(max_experience_years)
        except (ValueError, TypeError):
            max_experience_years = None
            
    job_code = normalize_to_isco(job_title)
    is_general_program = _is_general_trainee_program(job_title)

    # Membangun profil tag dinamis kandidat
    cv_tags = _build_dynamic_skill_profile(cv_tags_str, candidate_experiences)
    job_tags_clean = [t.strip().lower() for t in job_tags if t.strip()] if job_tags else []

    # 3. Entry-Level/MT/Intern logic (min_experience_years <= 1.0)
    if min_experience_years <= 1.0:
        total_months = 0  # Will be accumulated in the loop below (avoid double counting)

        if not candidate_experiences:
            # Kandidat tidak memiliki pengalaman kerja formal sama sekali.
            # Validasi ketat diperlukan untuk mencegah false positive pada posisi teknis.
            cv_field = cv_tags[0].strip().lower() if cv_tags else None
            job_field = job_tags_clean[0] if job_tags_clean else None

            if has_skills_match:
                # Ada kecocokan keahlian, tapi perlu validasi bidang CV vs bidang lowongan
                # untuk mencegah kandidat HR/Marketing lolos ke posisi IT hanya karena skill umum.
                if cv_field and job_field and not _are_fields_compatible(job_field, cv_field):
                    # BYPASS LOGIC: Entry-Level Sales/Admin/General Roles
                    if _is_bypass_allowed(job_title):
                        res = {
                            "decision": "PASS",
                            "match_type": "loosely_related",
                            "job_node": job_code,
                            "candidate_nodes": [],
                            "relevant_years": 0.0,
                            "total_years": 0.0,
                            "reason": (
                                f"Bypass Lintas Bidang: Fresh graduate diloloskan untuk posisi umum '{job_title}' "
                                f"meskipun bidang CV tidak kompatibel, karena menerima pelamar lintas bidang."
                            ),
                        }
                    else:
                        # Bypass Lintas Bidang Entry-Level / Magang: Lulusan lintas jurusan diloloskan jika memiliki
                        # kecocokan keahlian khusus dari proyek, tugas akhir, atau bootcamp.
                        if min_experience_years <= 1.0:
                            res = {
                                "decision": "PASS",
                                "match_type": "skills_match",
                                "job_node": job_code,
                                "candidate_nodes": [],
                                "relevant_years": 0.0,
                                "total_years": 0.0,
                                "reason": (
                                    f"Bypass Lintas Bidang Entry-Level: Kandidat fresh graduate lintas jurusan ({cv_field}) "
                                    f"diloloskan untuk posisi '{job_title}' karena memiliki kecocokan keahlian "
                                    f"({skills_str}) dari proyek/tugas akhir/bootcamp."
                                ),
                            }
                        else:
                            res = {
                                "decision": "FAIL",
                                "match_type": "field_mismatch",
                                "job_node": job_code,
                                "candidate_nodes": [],
                                "relevant_years": 0.0,
                                "total_years": 0.0,
                                "reason": (
                                    f"[Kesesuaian Posisi] Meskipun ada kecocokan keahlian ({skills_str}), bidang CV kandidat "
                                    f"({cv_field}) tidak kompatibel dengan bidang lowongan ({job_field}). "
                                    f"Kandidat tanpa pengalaman kerja dari bidang berbeda tidak diloloskan."
                                ),
                            }
                else:
                    res = {
                        "decision": "PASS",
                        "match_type": "skills_match",
                        "job_node": job_code,
                        "candidate_nodes": [],
                        "relevant_years": 0.0,
                        "total_years": 0.0,
                        "reason": (
                            f"Fresh graduate diloloskan berbasis kecocokan keahlian CV "
                            f"({skills_str}) meskipun belum memiliki pengalaman kerja formal."
                        ),
                    }
            else:
                # Tidak ada kecocokan keahlian sama sekali.
                # Hanya fresh graduate asli dengan jurusan relevan yang boleh UNKNOWN,
                # sisanya langsung FAIL untuk mencegah false positive.
                if is_fresh_graduate:
                    has_relevant_major = _check_major_relevance(
                        candidate_educations, job_title, job_tags
                    )
                    if has_relevant_major:
                        if min_experience_years == 0.0:
                            res = {
                                "decision": "PASS",
                                "match_type": "no_experience",
                                "job_node": job_code,
                                "candidate_nodes": [],
                                "relevant_years": 0.0,
                                "total_years": 0.0,
                                "reason": (
                                    f"Fresh graduate dengan jurusan relevan diloloskan untuk posisi junior "
                                    f"'{job_title}' (0 tahun pengalaman kerja)."
                                ),
                            }
                        else:
                            res = {
                                "decision": "UNKNOWN",
                                "match_type": "no_experience",
                                "job_node": job_code,
                                "candidate_nodes": [],
                                "relevant_years": 0.0,
                                "total_years": 0.0,
                                "reason": (
                                    f"Fresh graduate tanpa pengalaman kerja dan tanpa kecocokan keahlian, "
                                    f"namun memiliki jurusan yang relevan dengan posisi {job_title}. "
                                    f"Diloloskan sebagai UNKNOWN untuk ditinjau manual."
                                ),
                            }
                    else:
                        # BYPASS LOGIC: Entry-Level Sales/Admin/General Roles
                        if _is_bypass_allowed(job_title):
                            res = {
                                "decision": "PASS",
                                "match_type": "loosely_related",
                                "job_node": job_code,
                                "candidate_nodes": [],
                                "relevant_years": 0.0,
                                "total_years": 0.0,
                                "reason": (
                                    f"Bypass Lintas Bidang: Fresh graduate diloloskan untuk posisi umum '{job_title}' "
                                    f"meskipun jurusan berbeda, karena posisi ini menerima pelamar lintas bidang."
                                ),
                            }
                        else:
                            res = {
                                "decision": "FAIL",
                                "match_type": "no_experience",
                                "job_node": job_code,
                                "candidate_nodes": [],
                                "relevant_years": 0.0,
                                "total_years": 0.0,
                                "reason": (
                                    f"[Kesesuaian Posisi] Kandidat fresh graduate tanpa riwayat kerja, tidak memiliki kecocokan keahlian khusus, "
                                    f"dan latar belakang jurusan tidak relevan dengan posisi {job_title}."
                                ),
                            }
                else:
                    # BYPASS LOGIC: Entry-Level Sales/Admin/General Roles
                    if _is_bypass_allowed(job_title):
                        res = {
                            "decision": "PASS",
                            "match_type": "loosely_related",
                            "job_node": job_code,
                            "candidate_nodes": [],
                            "relevant_years": 0.0,
                            "total_years": 0.0,
                            "reason": (
                                f"Bypass Lintas Bidang: Fresh graduate diloloskan untuk posisi umum '{job_title}' "
                                f"meskipun jurusan berbeda, karena posisi ini menerima pelamar lintas bidang."
                            ),
                        }
                    else:
                        res = {
                            "decision": "FAIL",
                            "match_type": "no_experience",
                            "job_node": job_code,
                            "candidate_nodes": [],
                            "relevant_years": 0.0,
                            "total_years": 0.0,
                            "reason": (
                                f"[Kesesuaian Posisi] Kandidat tidak memiliki riwayat kerja formal dan tidak mencantumkan "
                                f"keahlian khusus di CV yang sesuai dengan posisi {job_title}."
                            ),
                        }
            if not relaxed:
                res["relaxed_result"] = res
            return res
        else:
            # Candidate has some work experiences (could be related or unrelated)
            relevant_months, total_months, best_match_type, candidate_codes, candidate_roles = _evaluate_all_experiences(
                candidate_experiences, job_code, job_title, job_tags, job_tags_clean
            )
            relevant_years = relevant_months / 12.0
            total_years = total_months / 12.0
            unique_roles = list(dict.fromkeys(candidate_roles))
            roles_str = ", ".join(unique_roles) if unique_roles else "Tidak diketahui"

            # Logging debug menggunakan logger bawaan untuk menghindari overhead print di production
            logger.debug(
                "best_match_type: %s, has_skills_match: %s, is_fresh_grad: %s",
                best_match_type,
                has_skills_match,
                is_fresh_graduate,
            )

            res = _make_entry_level_decision(
                relaxed, job_code, job_title, job_tags, best_match_type,
                relevant_years, total_years, candidate_codes, roles_str,
                has_skills_match, skills_str, is_fresh_graduate,
                is_general_program, max_experience_years,
                candidate_educations=candidate_educations,
                min_experience_years=min_experience_years
            )
            if not relaxed:
                res["relaxed_result"] = _make_entry_level_decision(
                    True, job_code, job_title, job_tags, best_match_type,
                    relevant_years, total_years, candidate_codes, roles_str,
                    has_skills_match, skills_str, is_fresh_graduate,
                    is_general_program, max_experience_years,
                    candidate_educations=candidate_educations,
                    min_experience_years=min_experience_years
                )
            return res

    # 4. Standard Professional Hires Logic (min_experience_years > 0)
    # Jika job title tidak dikenal, kita tidak bisa match -> pass through
    if job_code == "unknown":
        total_months = sum(_calc_experience_months(exp) for exp in candidate_experiences)
        res = {
            "decision": "UNKNOWN",
            "match_type": "unknown",
            "job_node": "unknown",
            "candidate_nodes": [],
            "relevant_years": total_months / 12.0,
            "total_years": total_months / 12.0,
            "reason": (
                f"Job title '{job_title}' tidak dikenali taxonomy (unknown). "
                f"Kandidat diloloskan untuk review manual."
            ),
        }
        if not relaxed:
            res["relaxed_result"] = res
        return res

    relevant_months, total_months, best_match_type, candidate_codes, candidate_roles = _evaluate_all_experiences(
        candidate_experiences, job_code, job_title, job_tags, job_tags_clean
    )
    relevant_years = relevant_months / 12.0
    total_years = total_months / 12.0
    unique_roles = list(dict.fromkeys(candidate_roles))
    roles_str = ", ".join(unique_roles) if unique_roles else "Tidak diketahui"

    if not candidate_experiences:
        res = {
            "decision": "FAIL",
            "match_type": "no_experience",
            "job_node": job_code,
            "candidate_nodes": [],
            "relevant_years": 0,
            "total_years": 0,
            "reason": "[Kesesuaian Posisi] Kandidat tidak memiliki pengalaman kerja.",
        }
        if not relaxed:
            res["relaxed_result"] = res
        return res

    res = _make_professional_decision(
        relaxed, job_code, job_title, job_tags, best_match_type,
        relevant_years, total_years, candidate_codes, roles_str,
        has_skills_match, skills_str, is_general_program,
        max_experience_years, min_experience_years, candidate_educations
    )
    if not relaxed:
        res["relaxed_result"] = _make_professional_decision(
            True, job_code, job_title, job_tags, best_match_type,
            relevant_years, total_years, candidate_codes, roles_str,
            has_skills_match, skills_str, is_general_program,
            max_experience_years, min_experience_years, candidate_educations
        )
    return res




def apply_taxonomy_filter(
    candidates: list,
    job_title: str,
    min_experience_years: float,
    job_tags: list[str] | None = None,
    max_experience_years: float | None = None,
) -> tuple[list, list, list, list[dict]]:
    """
    Menerapkan penyaringan berbasis taksonomi ISCO terhadap daftar kandidat secara single-pass.
    Membagi kandidat menjadi: lolos utama (passed), review utama (unknown),
    rekomendasi alternatif (relaxed/Tier 2), dan tereliminasi (eliminated).

    Parameter:
        candidates (list): Daftar kandidat (objek Require ORM) yang telah lolos hard filter.
        job_title (str): Judul posisi pekerjaan.
        min_experience_years (float): Batas minimum pengalaman kerja relevan.
        job_tags (list[str] | None): Daftar tag dari Job Description lowongan.
        max_experience_years (float | None): Batas maksimum pengalaman kerja yang diperbolehkan.

    Return:
        Tuple[list, list, list, list[dict]]: Daftar passed, unknown, relaxed (Tier 2), dan eliminated.
    """
    if min_experience_years is None:
        min_experience_years = 0.0
    else:
        try:
            min_experience_years = float(min_experience_years)
        except (ValueError, TypeError):
            min_experience_years = 0.0
            
    if max_experience_years is not None:
        try:
            max_experience_years = float(max_experience_years)
        except (ValueError, TypeError):
            max_experience_years = None
            
    passed = []
    unknown = []
    relaxed = []
    eliminated = []
    
    job_code = normalize_to_isco(job_title)
    logger.debug(f"[Taxonomy] Job Title: '{job_title}' -> ISCO Code: '{job_code}'")

    for candidate in candidates:
        name = f"{candidate.firstname or ''} {candidate.lastname or ''}".strip()
        rid = candidate.requireid
        is_fresh_grad = getattr(candidate, "is_fresh_graduate", False) or False

        cv_tags_str = getattr(candidate.cv_tags, "tags", "") if getattr(candidate, "cv_tags", None) else ""
        hard_skills_str = getattr(candidate.skills, "hard_skill", "") if getattr(candidate, "skills", None) else ""
        
        combined_tags = []
        if cv_tags_str:
            combined_tags.append(cv_tags_str)
        if hard_skills_str:
            combined_tags.append(hard_skills_str)
        cv_tags_str = ", ".join(combined_tags) if combined_tags else None
        
        # Impor lokal untuk menghindari dependensi sirkular
        from core.filtering.taxonomy_matcher import match_job_role
        
        # 1. Jalankan pencocokan dengan kriteria standar (relaxed=False)
        result_std = match_job_role(
            candidate.work_experiences,
            job_title,
            min_experience_years,
            cv_tags_str=cv_tags_str,
            job_tags=job_tags,
            candidate_educations=candidate.educations,
            max_experience_years=max_experience_years,
            is_fresh_graduate=is_fresh_grad,
            relaxed=False,
        )

        if result_std["decision"] == "PASS":
            passed.append((candidate, result_std))
        elif result_std["decision"] == "UNKNOWN":
            unknown.append((candidate, result_std))
        else:
            # 2. Jika gagal standar, cek apakah memenuhi kriteria relaxed
            # Gunakan hasil relaxed yang sudah dihitung bersamaan (single-pass) untuk efisiensi
            result_rel = result_std.get("relaxed_result")
            if result_rel and result_rel["decision"] in ("PASS", "UNKNOWN"):
                relaxed.append((candidate, result_rel))
            else:
                eliminated.append({
                    "require_id": rid,
                    "candidate_name": name,
                    "reason": result_std["reason"],
                    "match_type": result_std["match_type"],
                    "job_node": result_std["job_node"],
                    "candidate_nodes": result_std["candidate_nodes"],
                    "relevant_years": result_std["relevant_years"],
                    "total_years": result_std["total_years"],
                })

    logger.info(
        "ISCO Taxonomy filter: %d passed, %d unknown, %d relaxed (Tier 2), %d eliminated out of %d total",
        len(passed), len(unknown), len(relaxed), len(eliminated), len(candidates),
    )
    return passed, unknown, relaxed, eliminated

