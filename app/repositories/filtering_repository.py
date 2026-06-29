import logging
from datetime import datetime
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models import (
    Require,
    FilteringResult,
    RequireWorkExperience,
)

logger = logging.getLogger(__name__)


class FilteringRepository:
    """Repository for handling candidate and filtering results operations."""

    async def get_active_candidates(self, db: AsyncSession) -> list[Require]:
        """Fetch all active candidates with loaded relationships."""
        result = await db.execute(
            select(Require)
            .where((Require.is_delete == False) | (Require.is_delete == None))  # noqa: E711, E712
            .options(
                selectinload(Require.educations),
                selectinload(Require.work_experiences).selectinload(
                    RequireWorkExperience.experience_tags
                ),
                selectinload(Require.trainings),
                selectinload(Require.candidate_tags),
                selectinload(Require.candidate_skills),
            )
        )
        return list(result.scalars().all())

    async def get_applied_candidates(self, db: AsyncSession, job_vacancy_id: int) -> list[Require]:
        """
        Mengambil daftar kandidat yang melamar pada lowongan pekerjaan tertentu (job_vacancy_id).

        Parameter:
            db: Async database session.
            job_vacancy_id: ID lowongan pekerjaan.

        Return:
            list[Require]: Daftar objek Require kandidat yang melamar.
        """
        from app.models import ApplyJobs, User
        result = await db.execute(
            select(Require)
            .join(User, Require.user_id == User.id)
            .join(ApplyJobs, User.id == ApplyJobs.user_id)
            .where(ApplyJobs.job_vacancy_id == job_vacancy_id)
            .where((Require.is_delete == False) | (Require.is_delete == None))  # noqa: E711, E712
            .options(
                selectinload(Require.educations),
                selectinload(Require.work_experiences).selectinload(
                    RequireWorkExperience.experience_tags
                ),
                selectinload(Require.trainings),
                selectinload(Require.candidate_tags),
                selectinload(Require.candidate_skills),
            )
        )
        return list(result.scalars().all())

    async def save_result(
        self,
        db: AsyncSession,
        job_vacancy_id: int,
        require_id: int,
        candidate_name: str,
        stage: str,
        decision: str,
        reason: str | None = None,
        similarity_score: float | None = None,
    ) -> FilteringResult:
        """Menyimpan data hasil filtering untuk satu kandidat.

        Parameter:
            db (AsyncSession): Sesi database asinkron.
            job_vacancy_id (int): ID lowongan pekerjaan.
            require_id (int): ID profil kandidat pelamar.
            candidate_name (str): Nama lengkap kandidat.
            stage (str): Tahapan filter (misal: hard_filter, taxonomy_filter).
            decision (str): Keputusan kelayakan (LAYAK, REVIEW, ALTERNATIF, ELIMINATED).
            reason (str | None): Deskripsi alasan keputusan.
            similarity_score (float | None): Skor kecocokan semantik jika ada.

        Return:
            FilteringResult: Objek hasil filtering yang baru dibuat.
        """
        result = FilteringResult(
            job_vacancy_id=job_vacancy_id,
            require_id=require_id,
            candidate_name=candidate_name,
            stage=stage,
            decision=decision,
            reason=reason,
            similarity_score=similarity_score,
        )
        db.add(result)
        return result


    async def save_results_bulk(self, db: AsyncSession, results: list[dict]) -> None:
        """Save multiple filtering results in bulk using SQLAlchemy insert core statement."""
        if not results:
            return
        from sqlalchemy import insert
        from app.models import FilteringResult
        await db.execute(insert(FilteringResult), results)


    async def get_results_by_job_vacancy_id(self, db: AsyncSession, job_vacancy_id: int) -> list[FilteringResult]:
        """Mengambil seluruh data hasil filtering untuk ID lowongan tertentu.

        Parameter:
            db (AsyncSession): Sesi database asinkron.
            job_vacancy_id (int): ID lowongan pekerjaan.

        Return:
            list[FilteringResult]: Daftar objek hasil filtering.
        """
        result = await db.execute(
            select(FilteringResult).where(FilteringResult.job_vacancy_id == job_vacancy_id)
        )
        return list(result.scalars().all())

    async def get_eliminated_by_job_vacancy_id(self, db: AsyncSession, job_vacancy_id: int) -> list[FilteringResult]:
        """Mengambil semua hasil filtering yang berstatus eliminated (gagal filter) untuk lowongan tertentu.

        Mengecualikan status LAYAK, REVIEW, dan ALTERNATIF karena ketiganya bukan eliminasi mutlak.

        Parameter:
            db (AsyncSession): Sesi database asinkron.
            job_vacancy_id (int): ID lowongan pekerjaan.

        Return:
            list[FilteringResult]: Daftar hasil filtering yang berstatus eliminated.
        """
        result = await db.execute(
            select(FilteringResult).where(
                and_(
                    FilteringResult.job_vacancy_id == job_vacancy_id,
                    FilteringResult.decision.notin_(["LAYAK", "REVIEW", "ALTERNATIF"]),
                )
            )
        )
        return list(result.scalars().all())


    async def fetch_candidates_by_ids(self, db: AsyncSession, require_ids: list[int]) -> list[Require]:
        """Fetch candidates by their IDs with loaded relationships."""
        if not require_ids:
            return []
        result = await db.execute(
            select(Require)
            .where(Require.requireid.in_(require_ids))
            .options(
                selectinload(Require.educations),
                selectinload(Require.work_experiences).selectinload(
                    RequireWorkExperience.experience_tags
                ),
                selectinload(Require.trainings),
                selectinload(Require.candidate_tags),
                selectinload(Require.candidate_skills),
            )
        )
        return list(result.scalars().all())

    async def commit(self, db: AsyncSession) -> None:
        """Commit changes to the database."""
        await db.commit()

    async def delete_results_by_job_vacancy_id(self, db: AsyncSession, job_vacancy_id: int) -> None:
        """Menghapus seluruh hasil penyaringan (filtering results) lama untuk ID lowongan tertentu.

        Parameter:
            db (AsyncSession): Sesi database asinkron yang digunakan.
            job_vacancy_id (int): ID lowongan pekerjaan.

        Return:
            None
        """
        from sqlalchemy import delete
        from app.models import FilteringResult
        await db.execute(delete(FilteringResult).where(FilteringResult.job_vacancy_id == job_vacancy_id))


    async def get_last_batch_processed_time(self, db: AsyncSession) -> datetime | None:
        """Get the latest update time from candidate_tags."""
        from sqlalchemy import func
        from app.models import CandidateTag
        result = await db.execute(select(func.max(CandidateTag.updated_at)))
        return result.scalar()
