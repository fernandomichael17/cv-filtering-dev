"""Repository untuk manajemen data JobVacancy dan ParsedJobCache.

Menyediakan fungsi akses data lowongan pekerjaan (read-only) dari web karir
serta operasi penyimpanan cache hasil parsing LLM (read-write).
"""

import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import JobVacancy, ParsedJobCache

logger = logging.getLogger(__name__)


class JobRepository:
    """Repository untuk menangani operasi data lowongan pekerjaan (JobVacancy) dan cache parsing (ParsedJobCache)."""

    async def create_vacancy(
        self, db: AsyncSession, name: str, desc: str, spec: str | None = None
    ) -> JobVacancy:
        """
        Membuat lowongan pekerjaan baru (JobVacancy) di database.

        Parameter:
            db: Async database session.
            name: Nama lowongan pekerjaan.
            desc: Deskripsi lowongan pekerjaan.
            spec: Spesifikasi pekerjaan (opsional).

        Return:
            JobVacancy: Objek lowongan pekerjaan yang baru dibuat.
        """
        new_vacancy = JobVacancy(
            job_vacancy_name=name,
            job_vacancy_job_desc=desc,
            job_vacancy_job_spec=spec,
        )
        db.add(new_vacancy)
        await db.commit()
        await db.refresh(new_vacancy)
        return new_vacancy

    async def get_vacancy_by_id(self, db: AsyncSession, job_vacancy_id: int) -> JobVacancy | None:
        """
        Mengambil detail lowongan pekerjaan berdasarkan ID lowongan.

        Parameter:
            db: Async database session.
            job_vacancy_id: ID lowongan pekerjaan (job_vacancy_id).

        Return:
            JobVacancy | None: Objek lowongan atau None jika tidak ditemukan.
        """
        result = await db.execute(
            select(JobVacancy).where(JobVacancy.job_vacancy_id == job_vacancy_id)
        )
        return result.scalar_one_or_none()

    async def get_parsed_cache(self, db: AsyncSession, job_vacancy_id: int) -> ParsedJobCache | None:
        """
        Mengambil cache hasil parsing persyaratan lowongan berdasarkan ID lowongan.

        Parameter:
            db: Async database session.
            job_vacancy_id: ID lowongan pekerjaan.

        Return:
            ParsedJobCache | None: Objek cache hasil parsing atau None jika belum di-parse.
        """
        result = await db.execute(
            select(ParsedJobCache).where(ParsedJobCache.job_vacancy_id == job_vacancy_id)
        )
        return result.scalar_one_or_none()

    async def upsert_parsed_cache(
        self,
        db: AsyncSession,
        job_vacancy_id: int,
        parsed_requirements: dict,
        tags: list[str],
    ) -> ParsedJobCache:
        """
        Menyimpan atau memperbarui cache hasil parsing persyaratan lowongan.

        Parameter:
            db: Sesi database asinkron.
            job_vacancy_id: ID lowongan pekerjaan.
            parsed_requirements: Kamus data persyaratan terstruktur hasil parse LLM.
            tags: Daftar tag industri/keahlian dari lowongan.

        Return:
            ParsedJobCache: Objek cache yang berhasil disimpan/diperbarui.
        """
        existing = await self.get_parsed_cache(db, job_vacancy_id)
        if existing:
            existing.parsed_requirements = parsed_requirements
            existing.tags = tags
            await db.commit()
            await db.refresh(existing)
            return existing

        new_cache = ParsedJobCache(
            job_vacancy_id=job_vacancy_id,
            parsed_requirements=parsed_requirements,
            tags=tags,
        )
        db.add(new_cache)
        await db.commit()
        await db.refresh(new_cache)
        return new_cache

    async def list_all_vacancies(self, db: AsyncSession) -> list[JobVacancy]:
        """
        Mendaftar semua lowongan pekerjaan yang tersedia di web karir.

        Parameter:
            db: Async database session.

        Return:
            list[JobVacancy]: Daftar objek lowongan pekerjaan.
        """
        result = await db.execute(
            select(JobVacancy).order_by(JobVacancy.job_vacancy_id.desc())
        )
        return list(result.scalars().all())
