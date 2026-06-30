"""SQLAlchemy ORM models untuk CV Filtering v2.

Tabel milik CV-Filtering (READ-WRITE):
- candidate_tags: tag CV keseluruhan (pengganti tags_cv)
- candidate_experience_tags: tag per pengalaman kerja (pengganti tags_jobs)
- candidate_skills: hard skill, soft skill, bahasa (pengganti require_skills)
- parsed_job_cache: cache hasil parsing LLM untuk job_vacancy
- filtering_results: hasil filtering per kandidat

Tabel dari web karir (READ-ONLY):
- require: data utama kandidat
- requireeducation: riwayat pendidikan kandidat
- requireworkexperience: riwayat pengalaman kerja kandidat
- requiretraining: riwayat pelatihan/sertifikasi kandidat
- users: akun pengguna web karir
- job_vacancy: lowongan pekerjaan
- apply_jobs: relasi pelamar-lowongan
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    ForeignKey,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.database import Base


# ═══════════════════════════════════════════════════════════════
# Tabel milik CV-Filtering (READ-WRITE)
# ═══════════════════════════════════════════════════════════════


class CandidateTag(Base):
    """Tag CV keseluruhan kandidat (pengganti tags_cv).

    Menyimpan 3-5 tag utama yang merangkum profil kandidat,
    dihasilkan oleh LLM melalui extraction endpoint.
    """

    __tablename__ = "candidate_tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    require_id = Column(
        Integer,
        ForeignKey("require.requireid", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    tags = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    candidate = relationship("Require", back_populates="candidate_tags")


class CandidateExperienceTag(Base):
    """Tag per pengalaman kerja kandidat (pengganti tags_jobs).

    Format tags backward-compatible: "bidang, jabatan"
    Contoh: "IT & Software, Backend Developer"
    """

    __tablename__ = "candidate_experience_tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    work_id = Column(
        Integer,
        ForeignKey("requireworkexperience.workid", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    field_tag = Column(String(100), nullable=True)
    role_tag = Column(String(100), nullable=True)
    tags = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    work_experience = relationship(
        "RequireWorkExperience", back_populates="experience_tags"
    )


class CandidateSkill(Base):
    """Hard skill, soft skill, dan bahasa kandidat (pengganti require_skills).

    Setiap field berisi daftar skill yang dipisahkan koma.
    Dihasilkan oleh LLM melalui extraction endpoint.
    """

    __tablename__ = "candidate_skills"

    id = Column(Integer, primary_key=True, autoincrement=True)
    require_id = Column(
        Integer,
        ForeignKey("require.requireid", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    hard_skill = Column(Text, nullable=True)
    soft_skill = Column(Text, nullable=True)
    language = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    candidate = relationship("Require", back_populates="candidate_skills")


class ParsedJobCache(Base):
    """Cache hasil parsing LLM untuk job_vacancy.

    Menyimpan requirements terstruktur agar LLM tidak perlu dipanggil ulang
    untuk lowongan yang sama.
    """

    __tablename__ = "parsed_job_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_vacancy_id = Column(Integer, unique=True, nullable=False)
    parsed_requirements = Column(JSONB, nullable=True)
    tags = Column(JSONB, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class FilteringResult(Base):
    """Hasil filtering per kandidat untuk lowongan pekerjaan tertentu.

    Menghubungkan data lowongan (job_vacancy) dan profil pelamar (require).
    """

    __tablename__ = "filtering_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_vacancy_id = Column(
        Integer,
        ForeignKey("job_vacancy.job_vacancy_id", ondelete="CASCADE"),
        nullable=False,
    )
    require_id = Column(
        Integer,
        ForeignKey("require.requireid", ondelete="CASCADE"),
        nullable=False,
    )
    candidate_name = Column(String(255), nullable=True)
    stage = Column(String(50), nullable=False)
    decision = Column(String(50), nullable=False)
    reason = Column(Text, nullable=True)
    similarity_score = Column(Float, nullable=True)
    total_score = Column(Float, nullable=True)
    confidence = Column(String(50), nullable=True)
    score_breakdown = Column(JSONB, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # Hubungan relasi antar model
    job_vacancy = relationship("JobVacancy", back_populates="filtering_results")
    candidate = relationship("Require", back_populates="filtering_results")



# ═══════════════════════════════════════════════════════════════
# Tabel dari web karir (READ-ONLY)
# ═══════════════════════════════════════════════════════════════


class User(Base):
    """Akun pengguna web karir (read-only). Hanya kolom yang dibutuhkan untuk join."""

    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    is_delete = Column(Boolean, default=False)


class Require(Base):
    """Data utama kandidat dari web karir (read-only).

    Kolom dateofbirth bertipe VARCHAR di database aktual (bukan DateTime).
    Kolom tambahan q11, q14, q15, q16 untuk filter lokasi, gaji, dan ketersediaan.
    """

    __tablename__ = "require"
    __table_args__ = {"extend_existing": True}

    requireid = Column(Integer, primary_key=True)
    firstname = Column(String(255))
    middlename = Column(String(255), nullable=True)
    lastname = Column(String(255))
    gender = Column(String(20), nullable=True)
    dateofbirth = Column(String(50), nullable=True)  # VARCHAR di DB aktual
    cvpath = Column(String(500), nullable=True)
    photopath = Column(String(500), nullable=True)
    city = Column(String(255), nullable=True)
    address = Column(Text, nullable=True)
    gmail = Column(String(255), nullable=True)
    linkedin = Column(String(255), nullable=True)
    instagram = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    createdat = Column(DateTime, nullable=True)
    updatedat = Column(DateTime, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    marital_status = Column(String(50), nullable=True)
    is_fresh_graduate = Column(Boolean, default=False)
    q11_willing_outside_jakarta = Column(Boolean, nullable=True)
    q14_current_income = Column(Integer, nullable=True)
    q15_expected_income = Column(Integer, nullable=True)
    q16_available_from = Column(String(100), nullable=True)
    is_delete = Column(Boolean, default=False)

    # Relasi ke tabel hasil filtering
    filtering_results = relationship(
        "FilteringResult", back_populates="candidate", cascade="all, delete-orphan"
    )


    # Relationships ke tabel baru (milik CV-Filtering)
    candidate_tags = relationship(
        "CandidateTag", back_populates="candidate", uselist=False, lazy="selectin"
    )
    candidate_skills = relationship(
        "CandidateSkill", back_populates="candidate", uselist=False, lazy="selectin"
    )

    # Relationships ke tabel read-only
    educations = relationship(
        "RequireEducation", back_populates="candidate", lazy="selectin"
    )
    work_experiences = relationship(
        "RequireWorkExperience", back_populates="candidate", lazy="selectin"
    )
    trainings = relationship(
        "RequireTraining", back_populates="candidate", lazy="selectin"
    )


class RequireEducation(Base):
    """Riwayat pendidikan kandidat (read-only)."""

    __tablename__ = "requireeducation"
    __table_args__ = {"extend_existing": True}

    eduid = Column(Integer, primary_key=True)
    requireid = Column(Integer, ForeignKey("require.requireid"))
    institutionname = Column(String, nullable=True)
    major = Column(String, nullable=True)
    startdate = Column(DateTime, nullable=True)
    enddate = Column(DateTime, nullable=True)
    year = Column(Integer, nullable=True)
    score = Column(String, nullable=True)
    education_id = Column(Integer, nullable=True)
    startyear = Column(Integer, nullable=True)
    endyear = Column(Integer, nullable=True)

    candidate = relationship("Require", back_populates="educations")


class RequireWorkExperience(Base):
    """Riwayat pengalaman kerja kandidat (read-only)."""

    __tablename__ = "requireworkexperience"
    __table_args__ = {"extend_existing": True}

    workid = Column(Integer, primary_key=True)
    requireid = Column(Integer, ForeignKey("require.requireid"))
    companyname = Column(String, nullable=True)
    joblevel = Column(String, nullable=True)
    startdate = Column(DateTime, nullable=True)
    enddate = Column(DateTime, nullable=True)
    salary = Column(String, nullable=True)
    iscurrent = Column(Boolean, default=False)
    eexp_comments = Column(Text, nullable=True)
    jobdesk = Column(Text, nullable=True)
    startyear = Column(Integer, nullable=True)
    endyear = Column(Integer, nullable=True)

    candidate = relationship("Require", back_populates="work_experiences")
    experience_tags = relationship(
        "CandidateExperienceTag",
        back_populates="work_experience",
        uselist=False,
        lazy="selectin",
    )


class RequireTraining(Base):
    """Riwayat pelatihan/sertifikasi kandidat (read-only)."""

    __tablename__ = "requiretraining"
    __table_args__ = {"extend_existing": True}

    trainingid = Column(Integer, primary_key=True)
    requireid = Column(Integer, ForeignKey("require.requireid"))
    trainingname = Column(String, nullable=True)
    certificateno = Column(String, nullable=True)
    starttrainingdate = Column(DateTime, nullable=True)
    endtrainingdate = Column(DateTime, nullable=True)
    startyear = Column(Integer, nullable=True)
    endyear = Column(Integer, nullable=True)

    candidate = relationship("Require", back_populates="trainings")


class JobVacancy(Base):
    """Lowongan pekerjaan dari web karir (read-only).

    Struktur placeholder — perlu dikonfirmasi setelah user
    mengirim foto/akses database.
    """

    __tablename__ = "job_vacancy"
    __table_args__ = {"extend_existing": True}

    job_vacancy_id = Column(Integer, primary_key=True)
    job_vacancy_name = Column(String(255), nullable=True)
    job_vacancy_job_desc = Column(Text, nullable=True)
    job_vacancy_job_spec = Column(Text, nullable=True)

    # Relasi ke tabel hasil filtering
    filtering_results = relationship(
        "FilteringResult", back_populates="job_vacancy", cascade="all, delete-orphan"
    )



class ApplyJobs(Base):
    """Relasi pelamar-lowongan dari web karir (read-only).

    Struktur placeholder — perlu dikonfirmasi setelah user
    mengirim foto/akses database.
    """

    __tablename__ = "apply_jobs"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True)
    job_vacancy_id = Column(Integer, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
