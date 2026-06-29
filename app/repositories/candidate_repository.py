"""Repository untuk operasi CRUD tabel candidate_tags, candidate_experience_tags, candidate_skills."""

import logging
from datetime import datetime

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    CandidateTag,
    CandidateExperienceTag,
    CandidateSkill,
    Require,
)

logger = logging.getLogger(__name__)


async def get_candidate_by_user_id(session: AsyncSession, user_id: int) -> Require | None:
    """Mengambil data kandidat berdasarkan user_id.

    Parameter:
        session: Async database session.
        user_id: ID user dari tabel users.

    Return:
        Require | None: Objek kandidat atau None jika tidak ditemukan.
    """
    result = await session.execute(
        select(Require).where(Require.user_id == user_id, Require.is_delete == False)  # noqa: E712
    )
    return result.scalars().first()


async def upsert_candidate_tags(
    session: AsyncSession,
    require_id: int,
    tags: str,
) -> CandidateTag:
    """Menyimpan atau memperbarui tag CV keseluruhan kandidat.

    Parameter:
        session: Async database session.
        require_id: ID kandidat dari tabel require.
        tags: Tag CV dalam format comma-separated (misal: "IT & Software, Backend Development, Python").

    Return:
        CandidateTag: Objek tag yang disimpan.
    """
    result = await session.execute(
        select(CandidateTag).where(CandidateTag.require_id == require_id)
    )
    existing = result.scalars().first()

    if existing:
        existing.tags = tags
        existing.updated_at = datetime.now()
        return existing

    new_tag = CandidateTag(require_id=require_id, tags=tags)
    session.add(new_tag)
    return new_tag


async def upsert_candidate_skills(
    session: AsyncSession,
    require_id: int,
    hard_skill: str,
    soft_skill: str,
    language: str,
) -> CandidateSkill:
    """Menyimpan atau memperbarui skill kandidat.

    Parameter:
        session: Async database session.
        require_id: ID kandidat dari tabel require.
        hard_skill: Hard skills dalam format comma-separated.
        soft_skill: Soft skills dalam format comma-separated.
        language: Bahasa yang dikuasai dalam format comma-separated.

    Return:
        CandidateSkill: Objek skill yang disimpan.
    """
    result = await session.execute(
        select(CandidateSkill).where(CandidateSkill.require_id == require_id)
    )
    existing = result.scalars().first()

    if existing:
        existing.hard_skill = hard_skill
        existing.soft_skill = soft_skill
        existing.language = language
        existing.updated_at = datetime.now()
        return existing

    new_skill = CandidateSkill(
        require_id=require_id,
        hard_skill=hard_skill,
        soft_skill=soft_skill,
        language=language,
    )
    session.add(new_skill)
    return new_skill


async def upsert_experience_tags(
    session: AsyncSession,
    work_id: int,
    field_tag: str,
    role_tag: str,
    tags: str | None = None,
) -> CandidateExperienceTag:
    """Menyimpan atau memperbarui tag per pengalaman kerja.

    Parameter:
        session: Async database session.
        work_id: ID pengalaman kerja dari tabel requireworkexperience.
        field_tag: Kategori bidang (misal: "IT & Software").
        role_tag: Jabatan spesifik (misal: "Backend Developer").
        tags: Gabungan tag industri, peran, dan keahlian dari LLM (opsional).

    Return:
        CandidateExperienceTag: Objek tag yang disimpan.
    """
    result = await session.execute(
        select(CandidateExperienceTag).where(CandidateExperienceTag.work_id == work_id)
    )
    existing = result.scalars().first()
    tags_combined = tags if tags else (f"{field_tag}, {role_tag}" if field_tag and role_tag else (field_tag or role_tag or ""))

    if existing:
        existing.field_tag = field_tag
        existing.role_tag = role_tag
        existing.tags = tags_combined
        existing.updated_at = datetime.now()
        return existing

    new_tag = CandidateExperienceTag(
        work_id=work_id,
        field_tag=field_tag,
        role_tag=role_tag,
        tags=tags_combined,
    )
    session.add(new_tag)
    return new_tag


async def delete_experience_tags_by_require(
    session: AsyncSession,
    require_id: int,
) -> None:
    """Menghapus semua experience tags kandidat (untuk re-extraction).

    Parameter:
        session: Async database session.
        require_id: ID kandidat.

    Return:
        None
    """
    from sqlalchemy import text

    await session.execute(
        text(
            "DELETE FROM candidate_experience_tags "
            "WHERE work_id IN (SELECT workid FROM requireworkexperience WHERE requireid = :rid)"
        ),
        {"rid": require_id},
    )


async def get_tags_status(session: AsyncSession, require_id: int) -> dict:
    """Mengambil status tags dan skills kandidat.

    Parameter:
        session: Async database session.
        require_id: ID kandidat.

    Return:
        dict: Status tags kandidat.
    """
    tag_result = await session.execute(
        select(CandidateTag).where(CandidateTag.require_id == require_id)
    )
    tag = tag_result.scalars().first()

    skill_result = await session.execute(
        select(CandidateSkill).where(CandidateSkill.require_id == require_id)
    )
    skill = skill_result.scalars().first()

    exp_result = await session.execute(
        select(CandidateExperienceTag).join(
            CandidateExperienceTag.work_experience
        ).where(
            CandidateExperienceTag.work_experience.has(requireid=require_id)
        )
    )
    exp_tags = exp_result.scalars().all()

    return {
        "require_id": require_id,
        "has_tags": tag is not None,
        "cv_tags": tag.tags if tag else None,
        "tags": tag.tags if tag else None,
        "skills_extracted": skill is not None,
        "hard_skill": skill.hard_skill if skill else None,
        "soft_skill": skill.soft_skill if skill else None,
        "experience_tags_count": len(exp_tags),
        "updated_at": tag.updated_at if tag else None,
    }
