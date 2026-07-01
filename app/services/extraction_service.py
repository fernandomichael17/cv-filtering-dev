"""Service untuk orchestrasi extraction tags dan skills kandidat."""

import logging

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models import FilteringResult
from app.repositories import candidate_repository
from core.llm.candidate_tagger import tag_candidate

logger = logging.getLogger(__name__)


async def run_extraction(session: AsyncSession, user_id: int) -> dict:
    """Menjalankan proses extraction tags dan skills untuk kandidat.

    Alur:
    1. Cari kandidat berdasarkan user_id
    2. Panggil LLM untuk ekstraksi tags + skills
    3. Simpan hasil ke 3 tabel baru (upsert)

    Parameter:
        session: Async database session.
        user_id: ID user dari tabel users.

    Return:
        dict: Status hasil extraction.

    Exception:
        ValueError: Jika kandidat tidak ditemukan atau LLM gagal.
    """
    candidate = await candidate_repository.get_candidate_by_user_id(session, user_id)
    if not candidate:
        raise ValueError(f"Kandidat dengan user_id={user_id} tidak ditemukan")

    require_id = candidate.requireid
    logger.info("Memulai extraction untuk user_id=%d (require_id=%d)", user_id, require_id)

    extraction_result = await tag_candidate(candidate)

    await _save_extraction_result(session, candidate, extraction_result)

    # Hapus hasil filtering lama kandidat ini di PostgreSQL
    await session.execute(delete(FilteringResult).where(FilteringResult.require_id == require_id))

    await session.commit()

    logger.info("Extraction selesai untuk require_id=%d, data filtering lama telah dibersihkan", require_id)
    return {
        "status": "completed",
        "require_id": require_id,
        "cv_tags": extraction_result.get("cv_tags", ""),
        "experience_tags_count": len(extraction_result.get("experience_tags", [])),
        "skills": extraction_result.get("skills", {}),
    }


async def _save_extraction_result(
    session: AsyncSession,
    candidate,
    extraction_result: dict,
) -> None:
    """Menyimpan hasil extraction ke database (upsert ke 3 tabel).

    Parameter:
        session: Async database session.
        candidate: Objek ORM Require.
        extraction_result: Hasil dari tag_candidate().

    Return:
        None
    """
    require_id = candidate.requireid

    # 1. Simpan CV tags
    cv_tags_str = extraction_result.get("cv_tags", "")
    await candidate_repository.upsert_candidate_tags(session, require_id, cv_tags_str)

    # 2. Simpan skills
    skills = extraction_result.get("skills", {})
    hard_skill = skills.get("hard_skill", "")
    soft_skill = skills.get("soft_skill", "")
    language = skills.get("language", "")
    await candidate_repository.upsert_candidate_skills(
        session, require_id, hard_skill, soft_skill, language
    )

    # 3. Simpan experience tags
    await candidate_repository.delete_experience_tags_by_require(session, require_id)

    work_ids = {exp.workid for exp in (candidate.work_experiences or [])}
    for exp_tag in extraction_result.get("experience_tags", []):
        work_id = exp_tag.get("work_id")
        if work_id and work_id in work_ids:
            tags_str = exp_tag.get("tags", "")
            parts = [p.strip() for p in tags_str.split(",") if p.strip()]
            
            # Parsing field_tag dan role_tag secara lokal (0 = field, 1 = role)
            field_tag = parts[0] if len(parts) >= 1 else ""
            role_tag = parts[1] if len(parts) >= 2 else ""
            
            await candidate_repository.upsert_experience_tags(
                session,
                work_id=work_id,
                field_tag=field_tag,
                role_tag=role_tag,
                tags=tags_str,
            )
        else:
            logger.warning(
                "work_id=%s dari LLM tidak cocok dengan kandidat require_id=%d",
                work_id, require_id,
            )


async def run_extraction_task(user_id: int) -> None:
    """
    Menjalankan proses ekstraksi tag dan skill untuk kandidat tertentu di latar belakang.
    Fungsi ini membuka sesi database asinkron secara mandiri dan menangani kesalahan
    jika proses ekstraksi atau penyimpanan gagal.

    Parameter:
        user_id (int): ID pengguna dari tabel users.

    Return:
        None
    """
    async with async_session() as session:
        try:
            logger.info("Memulai background task run_extraction untuk user_id=%d", user_id)
            await run_extraction(session, user_id)
        except Exception as e:
            logger.error("Gagal menjalankan background task run_extraction untuk user_id=%d: %s", user_id, e)

