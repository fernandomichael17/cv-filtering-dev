"""Async SQLAlchemy database engine dan manajemen session."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """Kelas dasar untuk semua ORM model."""
    pass


async def get_db():
    """FastAPI dependency yang menyediakan async database session."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_tables():
    """Membuat tabel-tabel milik CV-Filtering jika belum ada.

    Tabel yang dibuat:
    - candidate_tags: tag CV keseluruhan (pengganti tags_cv)
    - candidate_experience_tags: tag per pengalaman kerja (pengganti tags_jobs)
    - candidate_skills: hard/soft skill dan bahasa (pengganti require_skills)
    - parsed_job_cache: cache hasil parsing LLM
    - filtering_results: hasil filtering per kandidat

    Return:
        None
    """
    from app.models import (  # noqa: F401
        CandidateTag,
        CandidateExperienceTag,
        CandidateSkill,
        ParsedJobCache,
        FilteringResult,
    )

    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all,
            tables=[
                CandidateTag.__table__,
                CandidateExperienceTag.__table__,
                CandidateSkill.__table__,
                ParsedJobCache.__table__,
                FilteringResult.__table__,
            ],
        )
