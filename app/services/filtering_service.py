"""Service utama untuk menjalankan alur penyaringan (filtering) CV.

Orchestrator untuk memproses:
1. Pemuatan Lowongan (JobVacancy) dan caching persyaratan terstruktur (ParsedJobCache).
2. Pemuatan Kandidat (pelamar terdaftar atau seluruh kandidat aktif).
3. Penyaringan Layer 1 (Hard Filter - Umur, Pendidikan, IPK, Sertifikasi Wajib).
4. Penyaringan Layer 1.5 (Category Filter - Kecocokan Bidang Industri).
5. Penyaringan Layer 2 (Taxonomy Filter - Kecocokan Peran berbasis ISCO).
6. Penyaringan Layer 1.7 (Skills Filter - Kecocokan Keahlian Wajib).
7. Skoring dan pemeringkatan kandidat.
8. Validasi keyakinan (confidence) oleh LLM untuk kandidat teratas.
9. Penyimpanan hasil akhir penyaringan secara massal.
"""

import asyncio
import logging
import time
import re
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Require, FilteringResult, ParsedJobCache
from app.repositories.job_repository import JobRepository
from app.repositories.filtering_repository import FilteringRepository
from app.repositories.local_metadata_repository import LocalMetadataRepository
from app.schemas.filtering import (
    FilteringResponse,
    CandidateResult,
    EducationInfo,
    ExperienceInfo,
    CertificationInfo,
    EliminatedCandidate,
    DirectFilteringResponse,
)
from core.filtering.hard_filter import apply_hard_filters
from core.filtering.taxonomy_matcher import apply_taxonomy_filter, match_job_role
from core.filtering.category_filter import get_job_category, check_category_compatibility
from core.filtering.skills_filter import apply_skills_filter
from core.filtering.scoring import calculate_candidate_score
from core.llm.jd_parser import parse_job_description
from core.utils.major_mapping import EDU_ID_TO_STR
from core.utils.reason_builder import build_candidate_reason
from core.utils.confidence import calculate_confidence

logger = logging.getLogger(__name__)


def _prewarm_caches(candidates: list, requirements: dict, job_tags: list[str] | None, job_title: str) -> None:
    """Pre-warm semantic matcher caches to avoid redundant embedding calculations."""
    try:
        from core.filtering.semantic_matcher import semantic_matcher
        texts_to_cache = set()
        
        # 1. Job tags prewarm
        for tag in (job_tags or []):
            texts_to_cache.add(f"passage: {tag.strip().lower()}")
            
        # 2. Majors prewarm
        allowed_majors = requirements.get("allowed_majors", [])
        if isinstance(allowed_majors, str):
            allowed_majors = [m.strip() for m in allowed_majors.split(",") if m.strip()]
        for m in allowed_majors:
            texts_to_cache.add(f"passage: {m.strip().lower()}")
            
        from core.filtering.hard_filter import _get_highest_education
        for c in candidates:
            edus = getattr(c, "educations", []) or []
            _, _, major, _ = _get_highest_education(edus)
            if major:
                texts_to_cache.add(f"query: {major.strip().lower()}")
                
        # 3. Skills prewarm
        req_skills = requirements.get("required_skills", []) or []
        pref_skills = requirements.get("preferred_skills", []) or []
        for skill in (req_skills + pref_skills):
            if skill:
                texts_to_cache.add(f"query: {skill.strip().lower()}")
                
        from core.utils.skill_helper import build_candidate_skills
        for c in candidates:
            cand_skills = build_candidate_skills(c)
            for skill in cand_skills:
                if skill:
                    texts_to_cache.add(f"passage: {skill.strip().lower()}")
                    
        # 4. Certifications prewarm
        req_certs = requirements.get("required_certifications", []) or []
        pref_certs = requirements.get("preferred_certifications", []) or []
        for cert in (req_certs + pref_certs):
            if cert:
                texts_to_cache.add(f"query: {cert.strip().lower()}")
                
        for c in candidates:
            for t in (getattr(c, "trainings", []) or []):
                cert_name = getattr(t, "trainingname", "")
                if cert_name:
                    texts_to_cache.add(f"passage: {cert_name.strip().lower()}")
            
        if texts_to_cache:
            semantic_matcher.prewarm_cache(list(texts_to_cache))
    except Exception as e:
        logger.warning("Gagal melakukan pre-warm caches: %s", e)


def adjust_score_by_tier(raw_score: float, decision: str) -> float:
    """Menghitung penyesuaian skor kandidat ke rentang absolut berdasarkan tier keputusan kelayakan.

    Membagi hasil ke rentang berikut:
    - LAYAK: [50.0, 100.0]
    - REVIEW: [30.0, 49.9]
    - ALTERNATIF: [0.0, 29.9]

    Parameter:
        raw_score (float): Skor awal kandidat (0 - 100).
        decision (str): Keputusan kelayakan ("LAYAK", "REVIEW", "ALTERNATIF").

    Return:
        float: Skor yang telah disesuaikan dan dibulatkan ke 1 desimal.
    """
    if decision == "LAYAK":
        return round(50.0 + (raw_score / 100.0 * 50.0), 1)
    elif decision == "REVIEW":
        return round(30.0 + (raw_score / 100.0 * 19.9), 1)
    elif decision == "ALTERNATIF":
        return round(raw_score / 100.0 * 29.9, 1)
    return round(raw_score, 1)


def get_score_degradation_reason(
    decision_status: str,
    is_alternative: bool,
    tax_match_type: str,
    has_required_skills: bool,
    hard_matched_count: int,
) -> str:
    """Mendapatkan penjelasan alasan penyesuaian/penurunan skor kandidat berdasarkan tier keputusan.

    Membantu pihak HRD memahami mengapa skor kecocokan kandidat diturunkan
    dan diklasifikasikan ke dalam tier REVIEW atau ALTERNATIF.

    Parameter:
        decision_status (str): Status keputusan kelayakan ("REVIEW" atau "ALTERNATIF").
        is_alternative (bool): Status apakah kandidat merupakan alternatif (relaxed matching).
        tax_match_type (str): Kategori tipe kecocokan taksonomi peran.
        has_required_skills (bool): Status apakah lowongan memiliki keahlian wajib.
        hard_matched_count (int): Jumlah keahlian wajib yang terpenuhi secara eksak.

    Return:
        str: String penjelasan alasan penurunan skor dalam Bahasa Indonesia formal.
    """
    if is_alternative:
        if has_required_skills and hard_matched_count == 0 and tax_match_type != "exact":
            return "kandidat direkomendasikan sebagai Kategori Alternatif karena tidak memiliki kecocokan eksak pada keahlian wajib yang disyaratkan."
        return "kandidat direkomendasikan sebagai Kategori Alternatif karena kecocokan taksonomi peran menggunakan pencocokan toleransi tinggi (relaxed matching)."

    if decision_status == "REVIEW":
        if tax_match_type in ("loosely_related", "skills_match"):
            return f"kandidat direkomendasikan sebagai Kategori Review untuk ditinjau manual karena kecocokan peran bertipe {tax_match_type.replace('_', ' ')}."
        return "kandidat direkomendasikan sebagai Kategori Review untuk ditinjau manual karena kualifikasi peran tidak dikenali secara penuh."

    return f"kandidat direkomendasikan sebagai Kategori {decision_status}."


class FilteringService:
    """Service untuk mengorkestrasi pipeline penyaringan CV secara lengkap."""

    # In-memory lock untuk menampung ID pekerjaan yang sedang diproses secara asinkron
    _active_jobs: set[int] = set()

    def __init__(self):
        self.job_repo = JobRepository()
        self.filtering_repo = FilteringRepository()
        self.local_repo = LocalMetadataRepository()

    def _build_candidate_result(
        self,
        candidate: Require,
        similarity_score: float | None = None,
        match_reason: str | None = None,
        total_score: float = 0.0,
        score_breakdown: dict | None = None,
        decision: str | None = None,
    ) -> CandidateResult:
        """Membangun objek data CandidateResult dari model ORM kandidat."""
        name = f"{candidate.firstname or ''} {candidate.lastname or ''}".strip()

        # Pendidikan tertinggi
        edu_info = None
        if candidate.educations:
            best_edu = max(
                candidate.educations,
                key=lambda e: getattr(e, "education_id", 0) or 0,
                default=None,
            )
            if best_edu:
                edu_id = getattr(best_edu, "education_id", None)
                edu_info = EducationInfo(
                    level=EDU_ID_TO_STR.get(edu_id, ""),
                    major=getattr(best_edu, "major", None),
                    university=getattr(best_edu, "institutionname", None),
                )

        # Daftar riwayat pengalaman
        experiences = []
        for exp in candidate.work_experiences:
            start_date = getattr(exp, "startdate", None)
            end_date = getattr(exp, "enddate", None)
            start_year = getattr(exp, "startyear", None)
            end_year = getattr(exp, "endyear", None)
            
            duration = 0
            if start_date and end_date:
                duration = int((end_date - start_date).days / 30.0)
            elif start_year and end_year:
                duration = (end_year - start_year) * 12
            elif start_year and getattr(exp, "iscurrent", False):
                duration = (datetime.now().year - start_year) * 12
                
            job_role = None
            exp_tags_obj = getattr(exp, "experience_tags", None)
            if exp_tags_obj:
                tags_str = getattr(exp_tags_obj, "tags", None)
                if tags_str:
                    parts = [p.strip() for p in tags_str.split(",")]
                    if len(parts) >= 2:
                        job_role = parts[1]
                    elif len(parts) == 1 and parts[0]:
                        job_role = parts[0]

            experiences.append(ExperienceInfo(
                job_title=getattr(exp, "joblevel", None),
                job_role=job_role,
                jobdesk=getattr(exp, "jobdesk", None),
                company=getattr(exp, "companyname", None),
                duration_months=duration if duration > 0 else None,
            ))

        # Sertifikasi / pelatihan
        certifications = [
            CertificationInfo(
                name=getattr(t, "trainingname", None),
                issuer=None,  # Kolom organizer tidak tersedia di db requiretraining
            )
            for t in candidate.trainings
        ]

        # Tag CV keseluruhan
        cv_tags_str = getattr(candidate.candidate_tags, "tags", None) if getattr(candidate, "candidate_tags", None) else None

        return CandidateResult(
            candidate_id=candidate.requireid,
            name=name,
            tags=cv_tags_str,
            education=edu_info,
            experiences=experiences,
            certifications=certifications,
            similarity_score=similarity_score,
            match_reason=match_reason,
            total_score=total_score,
            score_breakdown=score_breakdown,
            decision=decision,
        )

    async def _evaluate_top_candidates(
        self,
        job_title: str,
        job_description: str,
        requirements: dict,
        candidates: list[CandidateResult],
        min_experience_years: float = 0.0,
    ) -> list[CandidateResult]:
        """Validasi keakuratan kualifikasi kandidat teratas menggunakan LLM."""
        if not candidates:
            return candidates

        from core.llm.candidate_evaluator import evaluate_candidate_confidence
        import asyncio

        FLOOR = 10
        CEILING = 20
        DYNAMIC_DEVIATION = 15.0

        max_score = candidates[0].total_score
        score_threshold = max_score - DYNAMIC_DEVIATION

        dynamic_count = sum(1 for c in candidates if c.total_score >= score_threshold)
        num_to_eval = max(FLOOR, min(CEILING, dynamic_count))
        num_to_eval = min(num_to_eval, len(candidates))

        raw_top_n = candidates[:num_to_eval]
        top_n = []
        bypassed_alternatives = []
        
        for c in raw_top_n:
            if getattr(c, "is_alternative", False):
                bypassed_alternatives.append(c)
            else:
                top_n.append(c)
                
        remaining = bypassed_alternatives + candidates[num_to_eval:]

        # Ringkasan lowongan terstruktur
        reqs = requirements or {}
        job_summary_parts = []
        
        if reqs.get("required_skills"):
            skills_list = "\n  - ".join(reqs["required_skills"])
            job_summary_parts.append(f"Keahlian Wajib:\n  - {skills_list}")
            
        if reqs.get("preferred_skills"):
            pref_list = "\n  - ".join(reqs["preferred_skills"])
            job_summary_parts.append(f"Keahlian Tambahan:\n  - {pref_list}")
            
        if reqs.get("required_certifications"):
            certs_list = "\n  - ".join(reqs["required_certifications"])
            job_summary_parts.append(f"Sertifikasi Wajib:\n  - {certs_list}")
            
        if reqs.get("allowed_majors"):
            majors_list = "\n  - ".join(reqs["allowed_majors"])
            job_summary_parts.append(f"Jurusan yang Diterima:\n  - {majors_list}")
        
        desc_clean = re.sub(r'<[^>]+>', '', job_description or "").strip()
        desc_clean = re.sub(r'\s+', ' ', desc_clean)
        
        if not job_summary_parts:
            desc_fallback = desc_clean[:1000] + "..." if len(desc_clean) > 1000 else desc_clean
            job_summary_parts.append(f"Persyaratan & Tanggung Jawab (Teks Mentah):\n{desc_fallback}")
        else:
            desc_short = desc_clean[:200] + "..." if len(desc_clean) > 200 else desc_clean
            if desc_short:
                job_summary_parts.append(f"Tanggung Jawab Kerja:\n  - {desc_short}")
            
        job_summary_str = "\n\n".join(job_summary_parts)

        tasks = []
        for c in top_n:
            exp_list = []
            for i, exp in enumerate(c.experiences, 1):
                dur_str = ""
                if exp.duration_months:
                    years = exp.duration_months // 12
                    months = exp.duration_months % 12
                    if years > 0 and months > 0:
                        dur_str = f" ({years} tahun {months} bulan)"
                    elif years > 0:
                        dur_str = f" ({years} tahun)"
                    else:
                        dur_str = f" ({months} bulan)"
                
                title_str = exp.job_title or "Staf/Karyawan"
                comp_str = exp.company or "Perusahaan tidak diketahui"
                jobdesk_str = exp.jobdesk or "Tidak ada jobdesk"
                exp_list.append(f"Pengalaman {i}: {title_str} di {comp_str}{dur_str}\nJobdesk: {jobdesk_str}")
            exp_str = "\n\n".join(exp_list) if exp_list else "Tidak ada pengalaman"

            breakdown = c.score_breakdown or {}
            skills_info = breakdown.get("skills_match", {})
            taxonomy_info = breakdown.get("taxonomy_match", {})

            matched_required = ", ".join(skills_info.get("required_matched", [])) or "Tidak ada"
            matched_preferred = ", ".join(skills_info.get("preferred_matched", [])) or "Tidak ada"
            match_type = taxonomy_info.get("value", "unknown")

            tasks.append(
                evaluate_candidate_confidence(
                    candidate_id=c.candidate_id,
                    experience=exp_str,
                    job_title=job_title,
                    job_description=job_summary_str,
                    match_type=match_type,
                    matched_required=matched_required,
                    matched_preferred=matched_preferred,
                    min_experience_years=min_experience_years,
                )
            )

        try:
            logger.info("Memulai validasi LLM untuk %d kandidat teratas secara paralel...", len(top_n))
            evaluations = await asyncio.gather(*tasks)

            for idx, eval_result in enumerate(evaluations):
                original_score = top_n[idx].total_score
                multiplier = eval_result.get("penalty_multiplier", 0.0)
                adjusted_score = max(0.0, round(original_score * (1.0 - multiplier), 1))

                top_n[idx].score_before_adjustment = original_score
                top_n[idx].total_score = adjusted_score
                top_n[idx].match_reason = eval_result.get("reason", "Evaluasi tidak tersedia.")
                top_n[idx].llm_confidence = eval_result.get("confidence", "medium")

                if multiplier > 0.0:
                    logger.info(
                        "Penalti confidence: %s — skor %s -> %s (confidence: %s)",
                        top_n[idx].name, original_score, adjusted_score, eval_result.get("confidence")
                    )
        except Exception as llm_err:
            logger.error("Gagal melakukan evaluasi confidence kandidat: %s", llm_err)
            # Biarkan skor asli jika LLM evaluator gagal
            for cand in top_n:
                cand.match_reason = cand.match_reason or "Lolos penyaringan taksonomi dan keahlian."
                cand.llm_confidence = "medium"

        # Gabungkan kembali kandidat
        all_adjusted = top_n + remaining
        all_adjusted.sort(key=lambda x: x.total_score, reverse=True)
        return all_adjusted

    async def run_filtering(self, db: AsyncSession, job_id: int, mode: str = "registered") -> FilteringResponse:
        """
        Menjalankan alur pipa penyaringan CV secara lengkap untuk ID lowongan tertentu.

        Parameter:
            db: Async database session.
            job_id: ID lowongan pekerjaan.
            mode: Mode pencarian kandidat ("registered" untuk pelamar terdaftar, atau "mixmatch" untuk seluruh database).

        Return:
            FilteringResponse: Hasil akhir proses penyaringan terstruktur.
        """
        start_time = time.time()
        logger.info("Memulai pipeline filtering untuk Job ID: %d (Mode: %s)", job_id, mode)

        # 1. Ambil detail lowongan & cache parsing
        job_cache = await self.job_repo.get_parsed_cache(db, job_id)
        vacancy = await self.job_repo.get_vacancy_by_id(db, job_id)
        if not vacancy:
            raise ValueError(f"Lowongan pekerjaan (JobVacancy) dengan ID {job_id} tidak ditemukan")

        if not job_cache:
            logger.info("Cache persyaratan lowongan belum ada. Memulai parsing JD via LLM...")
            full_jd_text = f"Posisi: {vacancy.job_vacancy_name}\n\nDeskripsi: {vacancy.job_vacancy_job_desc or ''}\n\nSpesifikasi: {vacancy.job_vacancy_job_spec or ''}"
            parsed = await parse_job_description(full_jd_text)
            tags = parsed.pop("tags", [])
            job_cache = await self.job_repo.upsert_parsed_cache(
                db, job_id, parsed, tags
            )

        requirements = job_cache.parsed_requirements
        job_tags = job_cache.tags
        
        # Tentukan judul jabatan untuk pencocokan taksonomi (menggunakan Feature Flag)
        job_title = vacancy.job_vacancy_name
        if settings.USE_STANDARDIZED_TITLE_FOR_TAXO and requirements and requirements.get("standardized_title"):
            job_title = requirements["standardized_title"]
            logger.info("Menggunakan nama jabatan standar hasil LLM untuk taksonomi: '%s' (Judul asli: '%s')", job_title, vacancy.job_vacancy_name)

        # 2. Ambil kandidat berdasarkan mode dan saring yang sudah pernah diproses sebelumnya
        existing_results = await self.filtering_repo.get_results_by_job_vacancy_id(db, job_id)
        already_filtered_ids = {res.require_id for res in existing_results}
        logger.info("Ditemukan %d kandidat yang sudah pernah difilter sebelumnya untuk lowongan ini.", len(already_filtered_ids))

        if mode == "registered":
            all_candidates = await self.filtering_repo.get_applied_candidates(db, job_id)
            logger.info("Berhasil mengambil %d kandidat yang melamar lowongan ini.", len(all_candidates))
        else:
            all_candidates = await self.filtering_repo.get_active_candidates(db)
            logger.info("Berhasil mengambil seluruh %d kandidat aktif dari database untuk mix-match.", len(all_candidates))

        # Hanya menyaring kandidat baru yang belum pernah diproses
        all_candidates = [c for c in all_candidates if c.requireid not in already_filtered_ids]
        logger.info("Jumlah kandidat baru yang akan diproses: %d (dari total %d kandidat)", len(all_candidates), len(all_candidates) + len(already_filtered_ids))

        if not all_candidates:
            logger.info("Tidak ada kandidat baru untuk difilter. Mengambil hasil dari database.")
            return await self.get_results(db, job_id)

        total_candidates = len(all_candidates)

        # 3. Layer 1 — Hard filter
        passed_hard, eliminated_hard = apply_hard_filters(all_candidates, requirements)
        logger.info("Hard filter selesai. Lolos: %d, Gugur: %d", len(passed_hard), len(eliminated_hard))

        # Kumpulkan data eliminasi
        results_to_save = []
        for elim in eliminated_hard:
            results_to_save.append({
                "job_vacancy_id": job_id,
                "require_id": elim["require_id"],
                "candidate_name": elim["candidate_name"],
                "stage": "hard_filter",
                "decision": "ELIMINATED",
                "reason": elim["reason"],
                "similarity_score": None,
            })


        # 4. Layer 1.5 — Category filter
        compatible_categories = requirements.get("compatible_categories", [])
        if not compatible_categories and job_tags:
            job_category = get_job_category(job_tags)
            if job_category:
                compatible_categories = [c.strip() for c in job_category.split(",") if c.strip()]

        passed_category = []
        eliminated_category = []

        if compatible_categories:
            for candidate in passed_hard:
                name = f"{candidate.firstname or ''} {candidate.lastname or ''}".strip()
                cat_result = check_category_compatibility(
                    candidate.work_experiences,
                    compatible_categories,
                )
                if cat_result["compatible"]:
                    passed_category.append(candidate)
                else:
                    eliminated_category.append({
                        "require_id": candidate.requireid,
                        "candidate_name": name,
                        "reason": cat_result["reason"],
                    })
            
            for elim in eliminated_category:
                results_to_save.append({
                    "job_vacancy_id": job_id,
                    "require_id": elim["require_id"],
                    "candidate_name": elim["candidate_name"],
                    "stage": "category_filter",
                    "decision": "ELIMINATED",
                    "reason": elim["reason"],
                    "similarity_score": None,
                })

            logger.info("Category filter selesai. Lolos: %d, Gugur: %d", len(passed_category), len(eliminated_category))
        else:
            passed_category = passed_hard

        # Pre-warm semantic caches
        await asyncio.to_thread(_prewarm_caches, passed_category, requirements, job_tags, job_title)

        # 5. Layer 2 — Taxonomy matching
        min_exp_years = requirements.get("min_experience_years", 0)
        max_exp_years = requirements.get("max_experience_years")
        passed_taxonomy, unknown_taxonomy, relaxed_taxonomy, eliminated_taxonomy = apply_taxonomy_filter(
            passed_category,
            job_title=job_title,
            min_experience_years=min_exp_years,
            job_tags=job_tags,
            max_experience_years=max_exp_years,
        )

        for elim in eliminated_taxonomy:
            results_to_save.append({
                "job_vacancy_id": job_id,
                "require_id": elim["require_id"],
                "candidate_name": elim["candidate_name"],
                "stage": "taxonomy_filter",
                "decision": "ELIMINATED",
                "reason": elim["reason"],
                "similarity_score": None,
            })


        # Gabungkan kandidat untuk diproses oleh Skills Filter
        candidates_with_tax = passed_taxonomy + unknown_taxonomy
        candidates_for_skills = [c for c, _ in candidates_with_tax]
        taxonomy_results = {c.requireid: res for c, res in candidates_with_tax}

        # 6. Layer 1.7 — Skills filter
        passed_skills, eliminated_skills = apply_skills_filter(
            candidates_for_skills, requirements, taxonomy_results=taxonomy_results
        )

        for elim in eliminated_skills:
            results_to_save.append({
                "job_vacancy_id": job_id,
                "require_id": elim["require_id"],
                "candidate_name": elim["candidate_name"],
                "stage": "skills_filter",
                "decision": "ELIMINATED",
                "reason": elim["reason"],
                "similarity_score": None,
            })


        passed_skills_ids = {c.requireid for c in passed_skills}
        final_candidates = [(c, res) for c, res in candidates_with_tax if c.requireid in passed_skills_ids]

        # Proses kandidat alternatif (Tier 2/relaxed_taxonomy) jika ada
        if relaxed_taxonomy:
            candidates_for_relaxed_skills = [c for c, _ in relaxed_taxonomy]
            relaxed_taxonomy_results = {c.requireid: res for c, res in relaxed_taxonomy}
            passed_relaxed_skills, eliminated_relaxed_skills = apply_skills_filter(
                candidates_for_relaxed_skills, requirements, taxonomy_results=relaxed_taxonomy_results
            )
            passed_relaxed_ids = {c.requireid for c in passed_relaxed_skills}
            
            for c, res in relaxed_taxonomy:
                if c.requireid in passed_relaxed_ids:
                    res["is_relaxed"] = True
                    final_candidates.append((c, res))
                
            for elim in eliminated_relaxed_skills:
                results_to_save.append({
                    "job_vacancy_id": job_id,
                    "require_id": elim["require_id"],
                    "candidate_name": elim["candidate_name"],
                    "stage": "skills_filter_alternative",
                    "decision": "ELIMINATED",
                    "reason": f"[Kandidat Alternatif] {elim['reason']}",
                    "similarity_score": None,
                })


        # 7. Skoring Kandidat
        temp_candidates = []
        for candidate, result in final_candidates:
            score, breakdown = calculate_candidate_score(candidate, requirements, result, job_title)
            cand_res = self._build_candidate_result(
                candidate,
                similarity_score=None,
                match_reason=result["reason"],
                total_score=score,
                score_breakdown=breakdown,
            )
            cand_res.is_alternative = result.get("is_relaxed", False)
            temp_candidates.append((candidate, cand_res))

        temp_candidates.sort(key=lambda x: x[1].total_score, reverse=True)
        qualified_candidates = [item[1] for item in temp_candidates]

        # 8. Validasi keyakinan (confidence) LLM untuk kandidat teratas (opsional)
        if settings.ENABLE_LLM_EVALUATOR:
            # DB Session Decoupling — commit sesi sebelum LLM call agar tidak memblock pool
            try:
                await db.commit()
                await db.close()
            except Exception as db_err:
                logger.warning("Gagal menutup sesi database sebelum evaluasi LLM: %s", db_err)

            qualified_candidates = await self._evaluate_top_candidates(
                job_title=job_title,
                job_description=vacancy.job_vacancy_job_desc or "",
                requirements=requirements,
                candidates=qualified_candidates,
                min_experience_years=float(min_exp_years),
            )
        else:
            logger.info("LLM Evaluator dinonaktifkan. Menggunakan skor deterministic.")

        # 9. Menyimpan hasil akhir penyaringan ke database (membuka sesi baru)
        from app.database import async_session
        async with async_session() as save_db:
            unknown_require_ids = {c.requireid for c, _ in unknown_taxonomy}
            final_saved_candidates = []

            for candidate, cand_res in temp_candidates:
                # Sinkronkan skor & alasan dari LLM evaluator (jika aktif)
                if settings.ENABLE_LLM_EVALUATOR:
                    eval_res = next((qc for qc in qualified_candidates if qc.candidate_id == cand_res.candidate_id), None)
                    if eval_res:
                        cand_res.total_score = eval_res.total_score
                        cand_res.match_reason = eval_res.match_reason
                        cand_res.score_before_adjustment = eval_res.score_before_adjustment
                        cand_res.llm_confidence = eval_res.llm_confidence

                breakdown = cand_res.score_breakdown or {}
                tax_match_type = breakdown.get("taxonomy_match", {}).get("value", "unknown")
                required_matched = breakdown.get("skills_match", {}).get("required_matched", [])
                has_required_requirements = bool(requirements.get("required_skills"))
                hard_matched = [s for s in required_matched if "(semantic)" not in s]

                if cand_res.is_alternative:
                    decision_status = "ALTERNATIF"
                else:
                    if candidate.requireid in unknown_require_ids or tax_match_type in ("loosely_related", "skills_match"):
                        decision_status = "REVIEW"
                    else:
                        decision_status = "LAYAK"

                    if has_required_requirements and len(hard_matched) == 0 and tax_match_type != "exact":
                        decision_status = "ALTERNATIF"
                        cand_res.is_alternative = True

                raw_score = cand_res.total_score
                # Penyesuaian skor ke rentang absolut berdasarkan tier keputusan kelayakan (P12)
                cand_res.total_score = adjust_score_by_tier(raw_score, decision_status)

                cand_res.decision = decision_status

                # Hitung confidence level
                cand_res.confidence = calculate_confidence(breakdown, decision_status)

                # Bangun reason berdasarkan mode evaluator
                if settings.ENABLE_LLM_EVALUATOR and cand_res.llm_confidence:
                    db_reason = f"[{cand_res.llm_confidence.upper()}] {cand_res.match_reason}"
                else:
                    db_reason = build_candidate_reason(breakdown, decision_status)
                    
                # Tambahkan informasi skor asli jika skor disesuaikan (P12)
                if decision_status in ("REVIEW", "ALTERNATIF") and raw_score != cand_res.total_score:
                    has_req_skills = bool(requirements.get("required_skills"))
                    degrade_reason = get_score_degradation_reason(
                        decision_status=decision_status,
                        is_alternative=cand_res.is_alternative,
                        tax_match_type=tax_match_type,
                        has_required_skills=has_req_skills,
                        hard_matched_count=len(hard_matched)
                    )
                    db_reason += f" (Skor Kecocokan Asli: {raw_score:.1f}. Skor diturunkan karena {degrade_reason})"
                cand_res.match_reason = db_reason

                results_to_save.append({
                    "job_vacancy_id": job_id,
                    "require_id": cand_res.candidate_id,
                    "candidate_name": cand_res.name,
                    "stage": "taxonomy_filter",
                    "decision": decision_status,
                    "reason": db_reason,
                    "similarity_score": None,
                })

                final_saved_candidates.append(cand_res)

            # Simpan massal
            if results_to_save:
                await self.filtering_repo.save_results_bulk(save_db, results_to_save)
            await save_db.commit()

            # Simpan metadata analitik AI ke SQLite lokal secara asinkron
            local_meta_list = []
            for cand_res in final_saved_candidates:
                local_meta_list.append({
                    "require_id": cand_res.candidate_id,
                    "confidence": cand_res.confidence,
                    "total_score": cand_res.total_score,
                    "score_breakdown": cand_res.score_breakdown or {}
                })
            if local_meta_list:
                def save_local_meta():
                    self.local_repo.save_metadata_bulk(job_id, local_meta_list)
                await asyncio.to_thread(save_local_meta)

        return await self.get_results(db, job_id)


    async def get_results(self, db: AsyncSession, job_id: int) -> FilteringResponse:
        """
        Mengambil hasil penyaringan CV yang sudah disimpan untuk lowongan tertentu.

        Parameter:
            db (AsyncSession): Sesi database asinkron.
            job_id (int): ID lowongan pekerjaan.

        Return:
            FilteringResponse: Hasil akhir proses penyaringan terstruktur.
        """
        job_cache = await self.job_repo.get_parsed_cache(db, job_id)
        if not job_cache:
            raise ValueError(f"Job cache untuk ID {job_id} tidak ditemukan. Jalankan filter terlebih dahulu.")

        vacancy = await self.job_repo.get_vacancy_by_id(db, job_id)
        job_title = vacancy.job_vacancy_name if vacancy else "Unknown Job"
        
        # Tentukan judul jabatan untuk pencocokan taksonomi (menggunakan Feature Flag)
        if settings.USE_STANDARDIZED_TITLE_FOR_TAXO and job_cache and job_cache.parsed_requirements and job_cache.parsed_requirements.get("standardized_title"):
            job_title = job_cache.parsed_requirements["standardized_title"]

        all_results = await self.filtering_repo.get_results_by_job_vacancy_id(db, job_id)
        layak_results = [r for r in all_results if r.decision in ("LAYAK", "REVIEW", "ALTERNATIF")]

        # Ambil metadata AI dari SQLite lokal secara asinkron
        local_metadata = await asyncio.to_thread(self.local_repo.get_metadata_by_job_id, job_id)

        require_ids = [r.require_id for r in layak_results]
        candidates_orm = await self.filtering_repo.fetch_candidates_by_ids(db, require_ids)
        candidates_map = {c.requireid: c for c in candidates_orm}

        qualified_candidates = []
        min_exp_years = job_cache.parsed_requirements.get("min_experience_years", 0) if job_cache.parsed_requirements else 0

        for lr in layak_results:
            candidate = candidates_map.get(lr.require_id)
            if candidate:
                is_alt = (lr.decision == "ALTERNATIF")
                
                # Coba ambil data dari SQLite lokal terlebih dahulu
                meta = local_metadata.get(lr.require_id)
                if meta:
                    score = meta.get("total_score", 0.0)
                    breakdown = meta.get("score_breakdown", {})
                    confidence = meta.get("confidence", "low")
                    score_before = score
                    llm_confidence = None
                else:
                    # Fallback ke kalkulasi real-time jika metadata SQLite tidak ditemukan
                    cv_tags_str = getattr(candidate.candidate_tags, "tags", None) if getattr(candidate, "candidate_tags", None) else None
                    tax_result = match_job_role(
                        candidate.work_experiences,
                        job_title,
                        min_exp_years,
                        cv_tags_str=cv_tags_str,
                        job_tags=job_cache.tags,
                        candidate_educations=candidate.educations,
                        relaxed=is_alt,
                    )
                    score, breakdown = calculate_candidate_score(candidate, job_cache.parsed_requirements or {}, tax_result, job_title)
                    confidence = calculate_confidence(breakdown, lr.decision)
                    score_before = score

                    # Parse confidence level dari reason prefix (jika LLM evaluator aktif)
                    reason_str = lr.reason or ""
                    llm_confidence = None
                    reason_clean = reason_str

                    if settings.ENABLE_LLM_EVALUATOR:
                        for level in ("high", "medium", "low"):
                            prefix = f"[{level.upper()}]"
                            if reason_str.startswith(prefix):
                                llm_confidence = level
                                reason_clean = reason_str[len(prefix):].strip()
                                break

                        if llm_confidence:
                            from core.llm.candidate_evaluator import PENALTY_MULTIPLIER
                            multiplier = PENALTY_MULTIPLIER.get(llm_confidence, 0.0)
                            score = max(0.0, round(score * (1.0 - multiplier), 1))

                    # Penyesuaian skor fallback ke rentang absolut berdasarkan tier keputusan kelayakan (P12)
                    score = adjust_score_by_tier(score, lr.decision)

                reason_str = lr.reason or ""
                reason_clean = reason_str
                if settings.ENABLE_LLM_EVALUATOR:
                    for level in ("high", "medium", "low"):
                        prefix = f"[{level.upper()}]"
                        if reason_str.startswith(prefix):
                            reason_clean = reason_str[len(prefix):].strip()
                            break

                # Sinkronisasi format alasan jika terjadi kalkulasi ulang real-time pada get_results fallback
                if not meta and lr.decision in ("REVIEW", "ALTERNATIF") and score_before != score:
                    if "Skor Kecocokan Asli" not in reason_clean:
                        breakdown = breakdown or {}
                        tax_match_type = breakdown.get("taxonomy_match", {}).get("value", "unknown")
                        req_skills = (job_cache.parsed_requirements or {}).get("required_skills", [])
                        has_req_skills = bool(req_skills)
                        required_matched = breakdown.get("skills_match", {}).get("required_matched", [])
                        hard_matched = [s for s in required_matched if "(semantic)" not in s]
                        
                        degrade_reason = get_score_degradation_reason(
                            decision_status=lr.decision,
                            is_alternative=is_alt,
                            tax_match_type=tax_match_type,
                            has_required_skills=has_req_skills,
                            hard_matched_count=len(hard_matched)
                        )
                        reason_clean += f" (Skor Kecocokan Asli: {score_before:.1f}. Skor diturunkan karena {degrade_reason})"

                cand_res = self._build_candidate_result(
                    candidate,
                    similarity_score=lr.similarity_score,
                    match_reason=reason_clean,
                    total_score=score,
                    score_breakdown=breakdown,
                    decision=lr.decision,
                )
                cand_res.is_alternative = is_alt
                cand_res.confidence = confidence
                
                if settings.ENABLE_LLM_EVALUATOR and llm_confidence:
                    cand_res.score_before_adjustment = score_before
                    cand_res.llm_confidence = llm_confidence

                qualified_candidates.append(cand_res)

        qualified_candidates.sort(key=lambda x: x.total_score, reverse=True)
        last_batch = await self.filtering_repo.get_last_batch_processed_time(db)

        return FilteringResponse(
            job_vacancy_id=job_id,
            job_tags=job_cache.tags,
            total_candidates=len(all_results),
            after_hard_filter=len(layak_results),
            after_skills_filter=len(layak_results),
            after_taxonomy_filter=len(layak_results),
            duration_seconds=0.0,
            last_batch_processed=last_batch,
            candidates=qualified_candidates,
        )


    async def get_eliminated(self, db: AsyncSession, job_id: int) -> list[EliminatedCandidate]:
        """Mengambil daftar kandidat yang tereliminasi beserta alasannya."""
        vacancy = await self.job_repo.get_vacancy_by_id(db, job_id)
        if not vacancy:
            raise ValueError(f"Vacancy #{job_id} tidak ditemukan")

        eliminated = await self.filtering_repo.get_eliminated_by_job_vacancy_id(db, job_id)


        return [
            EliminatedCandidate(
                stage=e.stage,
                candidate_name=e.candidate_name or "Unknown",
                reason=e.reason,
            )
            for e in eliminated
        ]

    async def parse_and_filter(self, db: AsyncSession, title: str, description: str) -> DirectFilteringResponse:
        """Menganalisis JD secara instan, membuat lowongan dummy, dan langsung memfilternya."""
        total_start = time.time()
        
        # 1. Buat lowongan baru
        start_create = time.time()
        vacancy = await self.job_repo.create_vacancy(db, title, description)
        duration_create = time.time() - start_create
        
        # 2. Parse JD via LLM
        parsing_start = time.time()
        try:
            full_jd_text = f"Posisi: {title}\n\n{description}"
            parsed = await parse_job_description(full_jd_text)
            tags = parsed.pop("tags", [])
            await self.job_repo.upsert_parsed_cache(
                db, vacancy.job_vacancy_id, parsed, tags
            )
        except ValueError as e:
            logger.error("JD parsing gagal di parse-and-filter: %s", e)
            await self.job_repo.upsert_parsed_cache(
                db, vacancy.job_vacancy_id, {}, []
            )
            
        parsing_duration = time.time() - parsing_start
        
        # 3. Jalankan filtering pipeline (mode mixmatch karena belum ada pelamar terdaftar)
        filtering_start = time.time()
        filtering_res = await self.run_filtering(db, vacancy.job_vacancy_id, mode="mixmatch")
        filtering_duration = time.time() - filtering_start
        total_duration = time.time() - total_start
        
        return DirectFilteringResponse(
            job_vacancy_id=vacancy.job_vacancy_id,
            job_title=title,
            job_tags=filtering_res.job_tags,
            total_candidates=filtering_res.total_candidates,
            after_hard_filter=filtering_res.after_hard_filter,
            after_skills_filter=filtering_res.after_skills_filter,
            after_taxonomy_filter=filtering_res.after_taxonomy_filter,
            parsing_duration_seconds=round(parsing_duration, 2),
            filtering_duration_seconds=round(filtering_duration, 2),
            total_duration_seconds=round(total_duration, 2),
            last_batch_processed=filtering_res.last_batch_processed,
            candidates=filtering_res.candidates,
        )


    async def run_filtering_task(self, job_id: int, mode: str = "registered") -> None:
        """Menjalankan proses penyaringan CV di latar belakang dengan database session mandiri."""
        from app.database import async_session
        async with async_session() as db:
            try:
                logger.info("Memulai background task run_filtering untuk Job ID: %d", job_id)
                await self.run_filtering(db, job_id, mode=mode)
            except Exception as e:
                logger.error("Gagal menjalankan background task run_filtering untuk Job ID %d: %s", job_id, e)
            finally:
                self._active_jobs.discard(job_id)

    async def parse_and_filter_task(self, job_id: int, title: str, description: str) -> None:
        """Menjalankan parsing deskripsi kerja dan penyaringan di latar belakang."""
        from app.database import async_session
        async with async_session() as db:
            try:
                logger.info("Memulai background task parse_and_filter untuk Job ID: %d", job_id)
                
                # Parse JD via LLM
                full_jd_text = f"Posisi: {title}\n\n{description}"
                try:
                    parsed = await parse_job_description(full_jd_text)
                    tags = parsed.pop("tags", [])
                    await self.job_repo.upsert_parsed_cache(
                        db, job_id, parsed, tags
                    )
                except Exception as parse_err:
                    logger.error("JD parsing gagal di background task untuk Job ID #%d: %s", job_id, parse_err)
                    await self.job_repo.upsert_parsed_cache(db, job_id, {}, [])

                # Jalankan filtering mode mixmatch
                await self.run_filtering(db, job_id, mode="mixmatch")
            except Exception as e:
                logger.error("Gagal menjalankan background task parse_and_filter untuk Job ID %d: %s", job_id, e)
            finally:
                self._active_jobs.discard(job_id)
