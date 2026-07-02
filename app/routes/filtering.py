"""Route untuk operasi penyaringan (filtering) kandidat.

Menyediakan endpoint untuk:
1. Memicu penyaringan pelamar terdaftar (POST /api/jobs/{job_id}/filter).
2. Memicu penyaringan mix-match (POST /api/jobs/{job_id}/mix-match).
3. Mengambil hasil penyaringan (GET /api/jobs/{job_id}/results).
4. Mengambil kandidat tereliminasi (GET /api/jobs/{job_id}/eliminated).
5. Menganalisis JD instan & filter (POST /api/jobs/parse-and-filter).
"""

import logging
from typing import Union
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.filtering import (
    FilteringResponse,
    EliminatedCandidate,
    FilterTaskResponse,
)
from app.services.filtering_service import FilteringService
from app.dependencies.security import verify_filtering_key, verify_mix_match_key
from app.tasks import run_filtering_celery_task
from app.utils.redis_lock import is_job_active, set_job_active, remove_job_active

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/jobs", tags=["filtering"])

filtering_service = FilteringService()


@router.post("/{job_vacancy_id}/filter", response_model=Union[FilteringResponse, FilterTaskResponse], dependencies=[Depends(verify_filtering_key)])
async def run_filtering(
    job_vacancy_id: int,
    sync: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """
    Menjalankan pipa penyaringan CV untuk kandidat pelamar terdaftar secara asinkron atau sinkron.

    Parameter:
        job_vacancy_id (int): ID lowongan pekerjaan (job_vacancy_id).
        sync (bool): Jika True, proses dijalankan secara sinkron. Default adalah False.
        db (AsyncSession): Sesi database asinkron.

    Return:
        FilterTaskResponse: Informasi status tugas penyaringan.
    """
    job = await filtering_service.job_repo.get_vacancy_by_id(db, job_vacancy_id)
    if not job:
        raise HTTPException(status_code=404, detail="Lowongan tidak ditemukan")

    if is_job_active(job_vacancy_id):
        raise HTTPException(
            status_code=400,
            detail="Proses penyaringan sedang berjalan untuk lowongan ini."
        )

    if sync:
        set_job_active(job_vacancy_id)
        try:
            res = await filtering_service.run_filtering(db, job_vacancy_id, mode="registered")
            return res
        except Exception as e:
            logger.error("Penyaringan pelamar terdaftar sinkron gagal untuk Job #%d: %s", job_vacancy_id, e)
            raise HTTPException(status_code=500, detail=f"Penyaringan gagal: {str(e)}")
        finally:
            remove_job_active(job_vacancy_id)

    set_job_active(job_vacancy_id)
    run_filtering_celery_task.delay(job_vacancy_id, "registered")

    return FilterTaskResponse(
        job_vacancy_id=job_vacancy_id,
        status="processing",
        message="Penyaringan pelamar terdaftar sedang berjalan di latar belakang."
    )


@router.post("/{job_vacancy_id}/mix-match", response_model=Union[FilteringResponse, FilterTaskResponse], dependencies=[Depends(verify_mix_match_key)])
async def run_mix_match(
    job_vacancy_id: int,
    sync: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """
    Menjalankan penyaringan mix-match terhadap seluruh kandidat aktif secara asinkron atau sinkron.

    Parameter:
        job_vacancy_id (int): ID lowongan pekerjaan (job_vacancy_id).
        sync (bool): Jika True, proses dijalankan secara sinkron. Default adalah False.
        db (AsyncSession): Sesi database asinkron.

    Return:
        FilterTaskResponse: Informasi status tugas penyaringan.
    """
    job = await filtering_service.job_repo.get_vacancy_by_id(db, job_vacancy_id)
    if not job:
        raise HTTPException(status_code=404, detail="Lowongan tidak ditemukan")

    if is_job_active(job_vacancy_id):
        raise HTTPException(
            status_code=400,
            detail="Proses penyaringan sedang berjalan untuk lowongan ini."
        )

    if sync:
        set_job_active(job_vacancy_id)
        try:
            res = await filtering_service.run_filtering(db, job_vacancy_id, mode="mixmatch")
            return res
        except Exception as e:
            logger.error("Penyaringan mix-match sinkron gagal untuk Job #%d: %s", job_vacancy_id, e)
            raise HTTPException(status_code=500, detail=f"Penyaringan gagal: {str(e)}")
        finally:
            remove_job_active(job_vacancy_id)

    set_job_active(job_vacancy_id)
    run_filtering_celery_task.delay(job_vacancy_id, "mixmatch")

    return FilterTaskResponse(
        job_vacancy_id=job_vacancy_id,
        status="processing",
        message="Penyaringan mix-match seluruh database sedang berjalan di latar belakang."
    )


@router.get("/{job_vacancy_id}/results", response_model=FilteringResponse, dependencies=[Depends(verify_filtering_key)])
async def get_results(job_vacancy_id: int, db: AsyncSession = Depends(get_db)):
    """
    Mengambil hasil penyaringan CV yang sudah selesai diproses.

    Parameter:
        job_vacancy_id: ID lowongan pekerjaan.
        db: Async database session.

    Return:
        FilteringResponse: Daftar kandidat beserta rincian skor.
    """
    if is_job_active(job_vacancy_id):
        raise HTTPException(
            status_code=202,
            detail="Hasil belum siap. Penyaringan sedang berjalan di latar belakang."
        )

    try:
        return await filtering_service.get_results(db, job_vacancy_id)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Error retrieving filtering results: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{job_vacancy_id}/eliminated", response_model=list[EliminatedCandidate], dependencies=[Depends(verify_filtering_key)])
async def get_eliminated(job_vacancy_id: int, db: AsyncSession = Depends(get_db)):
    """
    Mengambil daftar kandidat yang tereliminasi beserta alasan eliminasinya.

    Parameter:
        job_vacancy_id: ID lowongan pekerjaan.
        db: Async database session.

    Return:
        list[EliminatedCandidate]: Daftar kandidat tereliminasi.
    """
    try:
        return await filtering_service.get_eliminated(db, job_vacancy_id)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Error retrieving eliminated candidates: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")




