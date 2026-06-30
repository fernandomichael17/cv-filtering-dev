"""Modul untuk mendefinisikan tugas latar belakang menggunakan Celery.

Membungkus proses LLM parsing, ekstraksi tag kandidat, dan pipeline
penyaringan CV secara asinkron agar terpisah dari process space web API.
"""

import asyncio
import logging
from celery import Celery

from app.config import settings
from app.utils.redis_lock import remove_job_active

logger = logging.getLogger(__name__)

# Inisialisasi Celery Application
celery_app = Celery(
    "cv_filtering_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Jakarta",
    enable_utc=True,
)


@celery_app.task
def run_job_parsing_celery_task(job_id: int, title: str, desc: str, spec: str | None) -> None:
    """Menjalankan parsing kualifikasi lowongan kerja via LLM di latar belakang.

    Parameter:
        job_id (int): ID lowongan pekerjaan (job_vacancy_id).
        title (str): Judul lowongan pekerjaan.
        desc (str): Deskripsi utama lowongan.
        spec (str | None): Spesifikasi/syarat tambahan lowongan.

    Return:
        None
    """
    from app.database import async_session, engine
    from app.repositories.job_repository import JobRepository
    from core.llm.jd_parser import parse_job_description

    async def _run():
        try:
            async with async_session() as session:
                try:
                    combined_jd = desc
                    if spec:
                        combined_jd = f"Description:\n{desc}\n\nRequirements/Specification:\n{spec}"
                    
                    full_jd_text = f"Posisi: {title}\n\n{combined_jd}"
                    parsed = await parse_job_description(full_jd_text)
                    tags = parsed.pop("tags", [])
                    
                    job_repo_local = JobRepository()
                    await job_repo_local.upsert_parsed_cache(
                        session, job_id, parsed, tags
                    )

                    # Bersihkan data hasil filtering lama karena kriteria lowongan berubah
                    from app.repositories.filtering_repository import FilteringRepository
                    filtering_repo = FilteringRepository()
                    
                    await filtering_repo.delete_results_by_job_vacancy_id(session, job_id)
                    await session.commit()
                    
                    logger.info("Job #%d JD berhasil di-parse asinkron oleh Celery dan hasil filtering lama telah dibersihkan. Tags: %s", job_id, tags)
                except Exception as e:
                    logger.error("JD parsing asinkron gagal untuk Job #%d di Celery: %s", job_id, e)
                    job_repo_local = JobRepository()
                    await job_repo_local.upsert_parsed_cache(session, job_id, {}, [])
        finally:
            await engine.dispose()

    asyncio.run(_run())


@celery_app.task
def run_extraction_celery_task(user_id: int) -> None:
    """Menjalankan proses ekstraksi tag dan skill kandidat via LLM di latar belakang.

    Parameter:
        user_id (int): ID pengguna dari tabel users.

    Return:
        None
    """
    from app.database import async_session, engine
    from app.services.extraction_service import run_extraction

    async def _run():
        try:
            async with async_session() as session:
                try:
                    logger.info("Memulai ekstraksi data kandidat untuk user_id=%d via Celery", user_id)
                    await run_extraction(session, user_id)
                except Exception as e:
                    logger.error("Gagal mengekstrak data kandidat untuk user_id=%d di Celery: %s", user_id, e)
        finally:
            await engine.dispose()

    asyncio.run(_run())


@celery_app.task
def run_filtering_celery_task(job_id: int, mode: str = "registered") -> None:
    """Menjalankan pipeline penyaringan CV kandidat di latar belakang.

    Parameter:
        job_id (int): ID lowongan pekerjaan (job_vacancy_id).
        mode (str): Mode penyaringan ("registered" atau "mixmatch").

    Return:
        None
    """
    from app.database import async_session, engine
    from app.services.filtering_service import FilteringService

    async def _run():
        try:
            service = FilteringService()
            async with async_session() as db:
                try:
                    logger.info("Memulai pipeline filter CV untuk Job ID: %d via Celery (mode: %s)", job_id, mode)
                    await service.run_filtering(db, job_id, mode=mode)
                except Exception as e:
                    logger.error("Gagal menjalankan pipeline filter CV untuk Job ID %d di Celery: %s", job_id, e)
                finally:
                    remove_job_active(job_id)
        finally:
            await engine.dispose()

    asyncio.run(_run())


@celery_app.task
def parse_and_filter_celery_task(job_id: int, title: str, description: str) -> None:
    """Menjalankan parsing deskripsi kerja instan diikuti penyaringan CV di latar belakang.

    Parameter:
        job_id (int): ID lowongan pekerjaan (job_vacancy_id).
        title (str): Judul lowongan pekerjaan.
        description (str): Deskripsi lengkap lowongan.

    Return:
        None
    """
    from app.database import async_session, engine
    from app.services.filtering_service import FilteringService
    from core.llm.jd_parser import parse_job_description

    async def _run():
        try:
            service = FilteringService()
            async with async_session() as db:
                try:
                    logger.info("Memulai parse dan filter instan untuk Job ID: %d via Celery", job_id)
                    full_jd_text = f"Posisi: {title}\n\n{description}"
                    try:
                        parsed = await parse_job_description(full_jd_text)
                        tags = parsed.pop("tags", [])
                        await service.job_repo.upsert_parsed_cache(
                            db, job_id, parsed, tags
                        )
                    except Exception as parse_err:
                        logger.error("JD parsing gagal di Celery task untuk Job ID #%d: %s", job_id, parse_err)
                        await service.job_repo.upsert_parsed_cache(db, job_id, {}, [])

                    await service.run_filtering(db, job_id, mode="mixmatch")
                except Exception as e:
                    logger.error("Gagal menjalankan parse dan filter untuk Job ID %d di Celery: %s", job_id, e)
                finally:
                    remove_job_active(job_id)
        finally:
            await engine.dispose()

    asyncio.run(_run())
