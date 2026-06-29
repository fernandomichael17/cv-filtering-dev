"""Router Simulator Job Portal dengan Database SQLite.

Menyediakan API untuk mengelola data lowongan kerja, akun pengguna,
dan profil kandidat di portal.db (SQLite) dan menyinkronkannya ke database PostgreSQL.
"""

import logging
import sqlite3
import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert

from app.database import get_db
from app.tasks import run_job_parsing_celery_task
from app.models import (
    User as PGUser,
    Require as PGRequire,
    RequireEducation as PGRequireEdu,
    RequireWorkExperience as PGRequireExp,
    RequireTraining as PGRequireTrain,
    JobVacancy as PGJob,
    ApplyJobs as PGApply,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/portal", tags=["portal-simulator"])

DB_FILE = "portal.db"


def get_sqlite_conn():
    """Membuka koneksi ke database SQLite portal.db.

    Return:
        sqlite3.Connection: Koneksi database SQLite.
    """
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_sqlite_db():
    """Menginisialisasi tabel-tabel SQLite portal.db jika belum ada.

    Sesuai dengan skema ERD yang disediakan oleh pengguna.
    """
    conn = get_sqlite_conn()
    cursor = conn.cursor()

    # 1. Tabel users
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        role TEXT,
        is_delete INTEGER DEFAULT 0,
        created_at TEXT,
        updated_at TEXT
    )
    """)

    # 2. Tabel require
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS require (
        requireid INTEGER PRIMARY KEY AUTOINCREMENT,
        firstname TEXT,
        middlename TEXT,
        lastname TEXT,
        gender TEXT,
        dateofbirth TEXT,
        cvpath TEXT,
        photopath TEXT,
        idcardpath TEXT,
        address TEXT,
        city TEXT,
        gmail TEXT,
        linkedin TEXT,
        instagram TEXT,
        phone TEXT,
        createdat TEXT,
        updatedat TEXT,
        admin_notes TEXT,
        status_updated_at TEXT,
        reviewed_by INTEGER,
        user_id INTEGER,
        trial310 TEXT,
        marital_status TEXT,
        is_fresh_graduate INTEGER DEFAULT 0,
        ref1_name TEXT, ref1_address_phone TEXT, ref1_occupation TEXT, ref1_relationship TEXT,
        ref2_name TEXT, ref2_address_phone TEXT, ref2_occupation TEXT, ref2_relationship TEXT,
        ref3_name TEXT, ref3_address_phone TEXT, ref3_occupation TEXT, ref3_relationship TEXT,
        emergency1_name TEXT, emergency1_address TEXT, emergency1_phone TEXT, emergency1_relationship TEXT,
        emergency2_name TEXT, emergency2_address TEXT, emergency2_phone TEXT, emergency2_relationship TEXT,
        q11_willing_outside_jakarta INTEGER DEFAULT 0,
        q14_current_income INTEGER,
        q15_expected_income INTEGER,
        q16_available_from TEXT,
        is_delete INTEGER DEFAULT 0
    )
    """)

    # 3. Tabel requireeducation
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS requireeducation (
        eduid INTEGER PRIMARY KEY AUTOINCREMENT,
        requireid INTEGER,
        institutionname TEXT,
        major TEXT,
        startdate TEXT,
        enddate TEXT,
        trial356 TEXT,
        year INTEGER,
        score REAL,
        education_id INTEGER,
        startyear INTEGER,
        endyear INTEGER
    )
    """)

    # 4. Tabel requiretraining
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS requiretraining (
        trainingid INTEGER PRIMARY KEY AUTOINCREMENT,
        requireid INTEGER,
        trainingname TEXT,
        certificateno TEXT,
        starttrainingdate TEXT,
        endtrainingdate TEXT,
        trial356 TEXT,
        startyear INTEGER,
        endyear INTEGER
    )
    """)

    # 5. Tabel requireworkexperience
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS requireworkexperience (
        workid INTEGER PRIMARY KEY AUTOINCREMENT,
        requireid INTEGER,
        companyname TEXT,
        joblevel TEXT,
        startdate TEXT,
        enddate TEXT,
        salary REAL,
        iscurrent INTEGER DEFAULT 0,
        trial359 TEXT,
        eexp_comments TEXT,
        jobdesk TEXT,
        startyear INTEGER,
        endyear INTEGER
    )
    """)

    # 6. Tabel job_vacancy
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS job_vacancy (
        job_vacancy_id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_request_hris_id INTEGER,
        job_title_hris_id INTEGER,
        job_vacancy_level_name TEXT,
        job_vacancy_name TEXT,
        job_vacancy_job_desc TEXT,
        job_vacancy_job_spec TEXT,
        job_vacancy_status_id INTEGER,
        job_vacancy_hris_location_id INTEGER,
        job_vacancy_start_date TEXT,
        job_vacancy_end_date TEXT,
        job_vacancy_man_power INTEGER,
        created_at TEXT,
        updated_at TEXT,
        trial307 TEXT
    )
    """)

    # 7. Tabel apply_jobs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS apply_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_vacancy_id INTEGER,
        user_id INTEGER
    )
    """)

    conn.commit()
    conn.close()
    logger.info("Database SQLite portal.db diinisialisasi sukses.")


# Panggil inisialisasi SQLite
init_sqlite_db()


# ═══════════════════════════════════════════════════════════════
# Pydantic Schemas untuk API Simulator
# ═══════════════════════════════════════════════════════════════

class JobCreateInput(BaseModel):
    """Schema input untuk membuat lowongan pekerjaan baru."""
    title: str
    description: str
    specification: str
    level_name: Optional[str] = "Staff"
    man_power: Optional[int] = 1


class EduInput(BaseModel):
    """Schema input riwayat pendidikan."""
    institution: str
    major: str
    year: int
    score: float
    startyear: int
    endyear: int


class TrainInput(BaseModel):
    """Schema input riwayat pelatihan."""
    name: str
    cert_no: str
    startyear: int
    endyear: int


class ExpInput(BaseModel):
    """Schema input riwayat pengalaman kerja."""
    company: str
    level: str
    jobdesk: str
    salary: float
    is_current: bool = False
    startyear: int
    endyear: int


class CandidateCreateInput(BaseModel):
    """Schema input pendaftaran kandidat baru."""
    name: str
    email: str
    password: str
    phone: str
    gender: str
    dob: str
    city: str
    address: str
    linkedin: Optional[str] = ""
    instagram: Optional[str] = ""
    is_fresh_graduate: bool = False
    willing_outside_jakarta: bool = True
    current_income: int = 0
    expected_income: int = 0
    available_from: str = "Immediately"
    education: List[EduInput] = []
    training: List[TrainInput] = []
    experience: List[ExpInput] = []


class ApplyInput(BaseModel):
    """Schema input lamaran pekerjaan."""
    job_vacancy_id: int
    user_id: int


# ═══════════════════════════════════════════════════════════════
# Helper Functions untuk Sinkronisasi PostgreSQL
# ═══════════════════════════════════════════════════════════════

async def sync_job_to_pg(db: AsyncSession, sqlite_id: int, job_data: JobCreateInput) -> int:
    """Sinkronisasi data lowongan kerja dari SQLite ke PostgreSQL.

    Parameter:
        db (AsyncSession): Sesi database PostgreSQL.
        sqlite_id (int): ID lowongan di SQLite.
        job_data (JobCreateInput): Data lowongan kerja.

    Return:
        int: ID lowongan di PostgreSQL.
    """
    pg_job = PGJob(
        job_vacancy_id=sqlite_id,
        job_vacancy_name=job_data.title,
        job_vacancy_job_desc=job_data.description,
        job_vacancy_job_spec=job_data.specification,
    )
    db.add(pg_job)
    await db.commit()
    return pg_job.job_vacancy_id


async def sync_candidate_to_pg(db: AsyncSession, sqlite_user_id: int, sqlite_req_id: int, data: CandidateCreateInput):
    """Sinkronisasi data lengkap kandidat ke PostgreSQL.

    Parameter:
        db (AsyncSession): Sesi database PostgreSQL.
        sqlite_user_id (int): ID user di SQLite.
        sqlite_req_id (int): ID require di SQLite.
        data (CandidateCreateInput): Data profil kandidat.
    """
    # 1. Simpan ke PG User
    pg_user = PGUser(
        id=sqlite_user_id,
        name=data.name,
        email=data.email,
    )
    db.add(pg_user)
    await db.flush()

    # Split nama depan/belakang
    names = data.name.split(" ", 1)
    first = names[0]
    last = names[1] if len(names) > 1 else ""

    # 2. Simpan ke PG Require
    pg_req = PGRequire(
        requireid=sqlite_req_id,
        firstname=first,
        lastname=last,
        gmail=data.email,
        phone=data.phone,
        gender=data.gender,
        dateofbirth=data.dob,
        city=data.city,
        address=data.address,
        linkedin=data.linkedin,
        instagram=data.instagram,
        is_fresh_graduate=data.is_fresh_graduate,
        q11_willing_outside_jakarta=data.willing_outside_jakarta,
        q14_current_income=data.current_income,
        q15_expected_income=data.expected_income,
        q16_available_from=data.available_from,
        user_id=sqlite_user_id,
    )
    db.add(pg_req)
    await db.flush()

    # 3. Simpan data Pendidikan
    for edu in data.education:
        pg_edu = PGRequireEdu(
            requireid=sqlite_req_id,
            institutionname=edu.institution,
            major=edu.major,
            year=edu.year,
            score=str(edu.score),
            startyear=edu.startyear,
            endyear=edu.endyear,
        )
        db.add(pg_edu)

    # 4. Simpan data Pelatihan
    for train in data.training:
        pg_train = PGRequireTrain(
            requireid=sqlite_req_id,
            trainingname=train.name,
            certificateno=train.cert_no,
            startyear=train.startyear,
            endyear=train.endyear,
        )
        db.add(pg_train)

    # 5. Simpan data Pengalaman
    for exp in data.experience:
        pg_exp = PGRequireExp(
            requireid=sqlite_req_id,
            companyname=exp.company,
            joblevel=exp.level,
            jobdesk=exp.jobdesk,
            salary=str(exp.salary),
            iscurrent=exp.is_current,
            startyear=exp.startyear,
            endyear=exp.endyear,
        )
        db.add(pg_exp)

    await db.commit()


# ═══════════════════════════════════════════════════════════════
# REST API Endpoints
# ═══════════════════════════════════════════════════════════════

@router.get("/schema")
async def get_db_schema():
    """Mengembalikan metadata skema database SQLite untuk visualisasi ERD.

    Return:
        dict: Struktur kolom dari ke-6 tabel.
    """
    tables = ["users", "require", "requireeducation", "requiretraining", "requireworkexperience", "job_vacancy"]
    schema = {}
    conn = get_sqlite_conn()
    cursor = conn.cursor()
    
    for t in tables:
        cursor.execute(f"PRAGMA table_info({t})")
        columns = cursor.fetchall()
        schema[t] = [
            {
                "cid": col["cid"],
                "name": col["name"],
                "type": col["type"],
                "notnull": bool(col["notnull"]),
                "dflt_value": col["dflt_value"],
                "pk": bool(col["pk"])
            }
            for col in columns
        ]
        
    conn.close()
    return schema


@router.get("/jobs")
async def list_portal_jobs():
    """Mengambil seluruh lowongan kerja dari SQLite portal.db.

    Return:
        list: Daftar lowongan kerja.
    """
    conn = get_sqlite_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM job_vacancy ORDER BY job_vacancy_id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.post("/jobs")
async def create_portal_job(job: JobCreateInput, db: AsyncSession = Depends(get_db)):
    """Membuat lowongan kerja baru di SQLite dan menyinkronkannya ke PostgreSQL.

    Parameter:
        job (JobCreateInput): Objek data lowongan kerja baru.
        db (AsyncSession): Sesi database PostgreSQL.

    Return:
        dict: Status sukses dan detail lowongan kerja yang disimpan.
    """
    conn = get_sqlite_conn()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()
    
    try:
        cursor.execute("""
        INSERT INTO job_vacancy (
            job_vacancy_name, job_vacancy_job_desc, job_vacancy_job_spec,
            job_vacancy_level_name, job_vacancy_man_power, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (job.title, job.description, job.specification, job.level_name, job.man_power, now_str, now_str))
        
        sqlite_id = cursor.lastrowid
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Gagal menulis ke SQLite: {str(e)}")
        
    conn.close()

    # Jalankan sinkronisasi ke PostgreSQL
    try:
        await sync_job_to_pg(db, sqlite_id, job)
    except Exception as e:
        logger.error("Gagal sinkronisasi lowongan ke PostgreSQL: %s", e)
        raise HTTPException(status_code=500, detail=f"SQLite disimpan, tapi sinkronisasi PG gagal: {str(e)}")

    # Picu tugas Celery asinkron untuk melakukan parsing kualifikasi via LLM
    try:
        run_job_parsing_celery_task.delay(sqlite_id, job.title, job.description, job.specification)
    except Exception as e:
        logger.warning("Gagal memicu tugas Celery parser LLM untuk lowongan #%d: %s", sqlite_id, e)

    return {"status": "success", "job_vacancy_id": sqlite_id, "title": job.title}


@router.get("/candidates")
async def list_portal_candidates():
    """Mengambil seluruh kandidat dari SQLite portal.db.

    Return:
        list: Daftar pelamar beserta relasi riwayat pendidikan/pengalamannya.
    """
    conn = get_sqlite_conn()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM require ORDER BY requireid DESC")
    candidates = [dict(r) for r in cursor.fetchall()]
    
    for c in candidates:
        req_id = c["requireid"]
        # Ambil education
        cursor.execute("SELECT * FROM requireeducation WHERE requireid = ?", (req_id,))
        c["education"] = [dict(r) for r in cursor.fetchall()]
        
        # Ambil training
        cursor.execute("SELECT * FROM requiretraining WHERE requireid = ?", (req_id,))
        c["training"] = [dict(r) for r in cursor.fetchall()]
        
        # Ambil experience
        cursor.execute("SELECT * FROM requireworkexperience WHERE requireid = ?", (req_id,))
        c["experience"] = [dict(r) for r in cursor.fetchall()]
        
    conn.close()
    return candidates


@router.post("/candidates")
async def register_portal_candidate(data: CandidateCreateInput, db: AsyncSession = Depends(get_db)):
    """Mendaftarkan kandidat baru di SQLite dan menyinkronkannya ke PostgreSQL.

    Parameter:
        data (CandidateCreateInput): Data profil kandidat lengkap.
        db (AsyncSession): Sesi database PostgreSQL.

    Return:
        dict: Status sukses dan ID kandidat yang tersimpan.
    """
    conn = get_sqlite_conn()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()

    try:
        # 1. Simpan user
        cursor.execute("""
        INSERT INTO users (name, email, password, role, created_at, updated_at)
        VALUES (?, ?, ?, 'candidate', ?, ?)
        """, (data.name, data.email, data.password, now_str, now_str))
        user_id = cursor.lastrowid

        # Split nama depan/belakang
        names = data.name.split(" ", 1)
        first = names[0]
        last = names[1] if len(names) > 1 else ""

        # 2. Simpan require
        cursor.execute("""
        INSERT INTO require (
            firstname, lastname, gmail, phone, gender, dateofbirth, city, address,
            linkedin, instagram, is_fresh_graduate, q11_willing_outside_jakarta,
            q14_current_income, q15_expected_income, q16_available_from, user_id, createdat, updatedat
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (first, last, data.email, data.phone, data.gender, data.dob, data.city, data.address,
              data.linkedin, data.instagram, 1 if data.is_fresh_graduate else 0, 1 if data.willing_outside_jakarta else 0,
              data.current_income, data.expected_income, data.available_from, user_id, now_str, now_str))
        req_id = cursor.lastrowid

        # 3. Simpan Education
        for edu in data.education:
            cursor.execute("""
            INSERT INTO requireeducation (requireid, institutionname, major, year, score, startyear, endyear)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (req_id, edu.institution, edu.major, edu.year, edu.score, edu.startyear, edu.endyear))

        # 4. Simpan Training
        for train in data.training:
            cursor.execute("""
            INSERT INTO requiretraining (requireid, trainingname, certificateno, startyear, endyear)
            VALUES (?, ?, ?, ?, ?)
            """, (req_id, train.name, train.cert_no, train.startyear, train.endyear))

        # 5. Simpan Experience
        for exp in data.experience:
            cursor.execute("""
            INSERT INTO requireworkexperience (requireid, companyname, joblevel, salary, iscurrent, jobdesk, startyear, endyear)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (req_id, exp.company, exp.level, exp.salary, 1 if exp.is_current else 0, exp.jobdesk, exp.startyear, exp.endyear))

        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        raise HTTPException(status_code=500, detail=f"Gagal menulis ke SQLite: {str(e)}")

    conn.close()

    # Jalankan sinkronisasi ke PostgreSQL
    try:
        await sync_candidate_to_pg(db, user_id, req_id, data)
    except Exception as e:
        logger.error("Gagal sinkronisasi kandidat ke PostgreSQL: %s", e)
        raise HTTPException(status_code=500, detail=f"SQLite disimpan, tapi sinkronisasi PG gagal: {str(e)}")

    return {"status": "success", "user_id": user_id, "require_id": req_id}


@router.post("/apply")
async def apply_job(data: ApplyInput, db: AsyncSession = Depends(get_db)):
    """Melamar lowongan pekerjaan (menghubungkan user ke job_vacancy).

    Parameter:
        data (ApplyInput): ID lowongan dan ID user.
        db (AsyncSession): Sesi database PostgreSQL.

    Return:
        dict: Status sukses.
    """
    conn = get_sqlite_conn()
    cursor = conn.cursor()
    
    try:
        # Cek jika sudah melamar di SQLite
        cursor.execute("SELECT id FROM apply_jobs WHERE job_vacancy_id = ? AND user_id = ?", (data.job_vacancy_id, data.user_id))
        if cursor.fetchone():
            conn.close()
            return {"status": "already_applied", "message": "Kandidat sudah melamar lowongan ini."}
            
        cursor.execute("INSERT INTO apply_jobs (job_vacancy_id, user_id) VALUES (?, ?)", (data.job_vacancy_id, data.user_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        raise HTTPException(status_code=500, detail=f"SQLite apply gagal: {str(e)}")
        
    conn.close()

    # Sinkronisasi ke PostgreSQL
    try:
        # Cek dulu di PG
        stmt = select(PGApply).where(
            PGApply.job_vacancy_id == data.job_vacancy_id,
            PGApply.user_id == data.user_id
        )
        res = await db.execute(stmt)
        if not res.scalars().first():
            pg_apply = PGApply(
                job_vacancy_id=data.job_vacancy_id,
                user_id=data.user_id
            )
            db.add(pg_apply)
            await db.commit()
    except Exception as e:
        logger.error("Gagal sinkronisasi apply_jobs ke PostgreSQL: %s", e)
        raise HTTPException(status_code=500, detail=f"SQLite disimpan, tapi sinkronisasi PG gagal: {str(e)}")

    return {"status": "success", "message": "Berhasil melamar lowongan kerja."}
