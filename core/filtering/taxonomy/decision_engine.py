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

from core.filtering.taxonomy.policies.entry_level import _make_entry_level_decision
from core.filtering.taxonomy.policies.professional import _make_professional_decision


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

