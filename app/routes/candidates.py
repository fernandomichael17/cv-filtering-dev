"""Route untuk extraction endpoint kandidat."""

import logging

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.candidates import ExtractionResponse, TagsStatusResponse
from app.services import extraction_service
from app.repositories import candidate_repository
from app.dependencies.security import verify_extract_tagger_key
from app.tasks import run_extraction_celery_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/candidates", tags=["Candidates"], dependencies=[Depends(verify_extract_tagger_key)])


@router.post("/{user_id}/extract-tags", response_model=ExtractionResponse)
async def extract_tags(
    user_id: int,
    sync: bool = False,
    session: AsyncSession = Depends(get_db),
):
    """
    Memicu proses ekstraksi tag dan skill kandidat secara asinkron atau sinkron.
    Endpoint ini memvalidasi keberadaan kandidat di database terlebih dahulu,
    kemudian menjadwalkan tugas Celery di latar belakang atau langsung menjalankannya secara sinkron.

    Parameter:
        user_id (int): ID pengguna dari tabel users.
        sync (bool): Jika True, ekstraksi dijalankan secara sinkron. Default adalah False.
        session (AsyncSession): Sesi database asinkron yang diinjeksi.

    Return:
        ExtractionResponse: Objek respon yang menunjukkan status proses.
    """
    candidate = await candidate_repository.get_candidate_by_user_id(session, user_id)
    if not candidate:
        raise HTTPException(status_code=404, detail=f"Kandidat dengan user_id={user_id} tidak ditemukan")

    if sync:
        try:
            res = await extraction_service.run_extraction(session, user_id)
            return ExtractionResponse(
                status="completed",
                require_id=res["require_id"],
                message=f"Ekstraksi selesai secara sinkron. CV Tags: {res['cv_tags']}. Skills: {res['skills']}",
            )
        except Exception as e:
            logger.error("Ekstraksi sinkron gagal untuk user_id=%d: %s", user_id, e)
            raise HTTPException(status_code=500, detail=f"Gagal melakukan ekstraksi LLM: {str(e)}")

    run_extraction_celery_task.delay(user_id)
    return ExtractionResponse(
        status="processing",
        require_id=candidate.requireid,
        message="Proses ekstraksi tag dan skill sedang berjalan di latar belakang.",
    )



@router.get("/{user_id}/tags", response_model=TagsStatusResponse)
async def get_tags_status(
    user_id: int,
    session: AsyncSession = Depends(get_db),
):
    """Mengecek status tags dan skills kandidat.

    Parameter:
        user_id: ID user dari tabel users.
        session: Async database session.

    Return:
        TagsStatusResponse: Status tags kandidat.
    """
    candidate = await candidate_repository.get_candidate_by_user_id(session, user_id)
    if not candidate:
        raise HTTPException(status_code=404, detail=f"Kandidat dengan user_id={user_id} tidak ditemukan")

    status = await candidate_repository.get_tags_status(session, candidate.requireid)
    return TagsStatusResponse(**status)
