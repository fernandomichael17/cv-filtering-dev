"""Route untuk manajemen lowongan pekerjaan (JobVacancy) dan cache persyaratan.

Menyediakan API untuk membuat lowongan, mendaftarkan semua lowongan,
serta mengambil detail lowongan beserta cache persyaratan terstrukturnya.
"""

import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories.job_repository import JobRepository
from app.schemas.jobs import JobCreate, JobResponse, JobListItem, JobParseRequest
from app.dependencies.security import verify_job_parser_key
from app.tasks import run_job_parsing_celery_task

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/jobs", tags=["jobs"], dependencies=[Depends(verify_job_parser_key)])

job_repo = JobRepository()


@router.post("", response_model=JobResponse)
async def parse_job(
    job: JobParseRequest,
    sync: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Memicu proses parsing kualifikasi lowongan pekerjaan yang sudah ada di database via LLM secara asinkron atau sinkron.

    Mengambil data lowongan yang terdaftar, lalu menjadwalkan tugas parsing Celery di latar belakang atau menjalankannya secara sinkron.

    Parameter:
        job (JobParseRequest): Objek request berisi ID lowongan dan opsional deskripsi/spesifikasi.
        sync (bool): Jika True, proses dijalankan secara sinkron dan mengembalikan durasi pemrosesan.
        db (AsyncSession): Sesi database asinkron.

    Return:
        JobResponse: Detail lowongan beserta status pemrosesan asinkron atau hasil sinkron.
    """
    # Tentukan judul, deskripsi, dan spesifikasi dari input payload
    title = job.title or "Unknown Position"
    desc = job.job_vacancy_job_desc if job.job_vacancy_job_desc is not None else (job.description or "")
    spec = job.job_vacancy_job_spec

    # Gunakan fallback database hanya jika data lowongan ditemukan
    vacancy = await job_repo.get_vacancy_by_id(db, job.job_vacancy_id)
    if vacancy:
        if not job.title:
            title = vacancy.job_vacancy_name or "Unknown Position"
        if job.job_vacancy_job_desc is None and not job.description:
            desc = vacancy.job_vacancy_job_desc or ""
        if job.job_vacancy_job_spec is None:
            spec = vacancy.job_vacancy_job_spec

    resp_desc = desc
    if spec:
        resp_desc = f"Description:\n{desc}\n\nSpecification:\n{spec}"

    if sync:
        import time
        from core.llm.jd_parser import parse_job_description
        from app.repositories.filtering_repository import FilteringRepository
        import asyncio

        start_time = time.time()

        # Proses parsing secara sinkron
        combined_jd = desc
        if spec:
            combined_jd = f"Description:\n{desc}\n\nRequirements/Specification:\n{spec}"
        full_jd_text = f"Posisi: {title}\n\n{combined_jd}"
        
        try:
            parsed = await parse_job_description(full_jd_text)
            tags = parsed.pop("tags", [])
        except Exception as e:
            logger.error("JD parsing sinkron gagal untuk Job #%d: %s", job.job_vacancy_id, e)
            raise HTTPException(status_code=500, detail=f"Gagal melakukan parsing LLM: {str(e)}")

        # Simpan ke cache
        await job_repo.upsert_parsed_cache(db, job.job_vacancy_id, parsed, tags)

        # Bersihkan data hasil filtering lama karena kriteria lowongan berubah
        filtering_repo = FilteringRepository()
        
        await filtering_repo.delete_results_by_job_vacancy_id(db, job.job_vacancy_id)
        await db.commit()

        duration = time.time() - start_time
        logger.info("Job #%d JD berhasil di-parse sinkron. Waktu: %.2fs. Tags: %s", job.job_vacancy_id, duration, tags)

        return JobResponse(
            job_vacancy_id=job.job_vacancy_id,
            title=title,
            description=resp_desc,
            parsed_requirements=parsed,
            tags=tags,
            parsing_duration_seconds=round(duration, 2),
            created_at=datetime.now(),
        )

    # 3. Jalankan parsing di latar belakang (asinkron via Celery)
    run_job_parsing_celery_task.delay(job.job_vacancy_id, title, desc, spec)

    return JobResponse(
        job_vacancy_id=job.job_vacancy_id,
        title=title,
        description=resp_desc,
        parsed_requirements=None,
        tags=None,
        parsing_duration_seconds=None,
        created_at=datetime.now(),
    )


@router.get("", response_model=list[JobListItem])
async def list_jobs(db: AsyncSession = Depends(get_db)):
    """
    Mendapatkan daftar seluruh lowongan pekerjaan yang tersedia.

    Parameter:
        db: Sesi database asinkron.

    Return:
        list[JobListItem]: Daftar lowongan terurut terbaru.
    """
    jobs = await job_repo.list_all_vacancies(db)
    return [
        JobListItem(
            job_vacancy_id=j.job_vacancy_id,
            title=j.job_vacancy_name or "Unknown Position",
            created_at=j.created_at if hasattr(j, "created_at") else datetime.now(),
        )
        for j in jobs
    ]


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: int, db: AsyncSession = Depends(get_db)):
    """
    Mendapatkan detail lowongan pekerjaan tertentu beserta kualifikasi terstrukturnya.

    Parameter:
        job_id: ID lowongan pekerjaan.
        db: Sesi database asinkron.

    Return:
        JobResponse: Detail lowongan dan persyaratan hasil parse LLM.
    """
    vacancy = await job_repo.get_vacancy_by_id(db, job_id)
    if not vacancy:
        raise HTTPException(status_code=404, detail="Lowongan tidak ditemukan")

    cache = await job_repo.get_parsed_cache(db, job_id)

    return JobResponse(
        job_vacancy_id=vacancy.job_vacancy_id,
        title=vacancy.job_vacancy_name or "",
        description=vacancy.job_vacancy_job_desc or "",
        parsed_requirements=cache.parsed_requirements if cache else None,
        tags=cache.tags if cache else None,
        created_at=cache.created_at if cache else datetime.now(),
    )
