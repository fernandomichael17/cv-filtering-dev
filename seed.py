"""Seed script — mengisi database dengan data kandidat dummy dan lowongan kerja.

Format data disesuaikan dengan skema database aktual (termasuk users,
job_vacancy, apply_jobs, serta pre-populate candidate_tags, candidate_skills,
dan candidate_experience_tags).
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "cvfiltering"),
    "user": os.getenv("DB_USER", "admin"),
    "password": os.getenv("DB_PASSWORD", "admin123"),
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": os.getenv("DB_PORT", "5433"),
}

CANDIDATES = [
    {
        "first": "Andi", "last": "Pratama",
        "email": "andi.pratama@mail.com", "phone": "081234567001",
        "city": "Jakarta", "address": "Jl. Sudirman No. 10, Jakarta Selatan",
        "gender": "Laki-laki", "dob": "1996-05-15", "is_fg": False,
        "current_income": 12000000, "expected_income": 15000000, "available_from": "Immediately",
        "education": [
            {"inst": "Universitas Indonesia", "major": "Teknik Informatika", "startyear": 2015, "endyear": 2019, "score": "3.65"},
        ],
        "experience": [
            {
                "company": "PT Tokopedia", "joblevel": "Backend Developer",
                "jobdesk": "Backend developer menggunakan Go dan PostgreSQL. Membangun microservices untuk payment gateway.",
                "startyear": 2021, "endyear": 2024,
                "field_tag": "IT & Software", "role_tag": "Backend Developer", "tags": "IT & Software, Backend Developer, Go, PostgreSQL"
            },
            {
                "company": "PT Bukalapak", "joblevel": "Junior Software Engineer",
                "jobdesk": "Membantu development fitur katalog produk menggunakan Python Django.",
                "startyear": 2019, "endyear": 2021,
                "field_tag": "IT & Software", "role_tag": "Backend Developer", "tags": "IT & Software, Backend Developer, Python, Django"
            },
        ],
        "training": [
            {"name": "AWS Certified Developer", "cert": "AWS-DEV-001"},
        ],
        # Precomputed tags dan skills agar tidak perlu memanggil LLM saat test
        "cv_tags": "IT, Web Development, Go, Python",
        "skills": {
            "hard": "Go, Python, Django, PostgreSQL, Microservices, AWS",
            "soft": "Problem Solving, Communication",
            "lang": "Indonesian, English"
        }
    },
    {
        "first": "Siti", "last": "Nurhaliza",
        "email": "siti.nurhaliza@mail.com", "phone": "081234567002",
        "city": "Bandung", "address": "Jl. Dago No. 55, Bandung",
        "gender": "Perempuan", "dob": "1997-08-20", "is_fg": False,
        "current_income": 15000000, "expected_income": 18000000, "available_from": "Immediately",
        "education": [
            {"inst": "Institut Teknologi Bandung", "major": "Ilmu Komputer", "startyear": 2014, "endyear": 2018, "score": "3.85"},
        ],
        "experience": [
            {
                "company": "PT Gojek", "joblevel": "Data Engineer",
                "jobdesk": "Data engineer, membangun ETL pipeline menggunakan Apache Spark dan Airflow. Mengelola data warehouse di BigQuery.",
                "startyear": 2018, "endyear": 2023,
                "field_tag": "IT & Software", "role_tag": "Data Engineer", "tags": "IT & Software, Data Engineer, Apache Spark, Airflow"
            },
        ],
        "training": [
            {"name": "Google Cloud Professional Data Engineer", "cert": "GCP-DE-002"},
        ],
        "cv_tags": "IT, Data Engineering, Spark, GCP",
        "skills": {
            "hard": "Apache Spark, Airflow, BigQuery, Python, ETL, GCP",
            "soft": "Analytical Thinking",
            "lang": "Indonesian, English"
        }
    },
    {
        "first": "Budi", "last": "Santoso",
        "email": "budi.santoso@mail.com", "phone": "081234567003",
        "city": "Surabaya", "address": "Jl. Pemuda No. 22, Surabaya",
        "gender": "Laki-laki", "dob": "1998-02-10", "is_fg": False,
        "current_income": 5000000, "expected_income": 6000000, "available_from": "1 month",
        "education": [
            {"inst": "Universitas Airlangga", "major": "Manajemen", "startyear": 2016, "endyear": 2020, "score": "3.20"},
        ],
        "experience": [
            {
                "company": "PT Bank BCA", "joblevel": "Staff Administrasi",
                "jobdesk": "Staff administrasi dan pengelolaan dokumen nasabah. Input data dan pembuatan laporan bulanan.",
                "startyear": 2020, "endyear": 2023,
                "field_tag": "Administration", "role_tag": "Administration Staff", "tags": "Administration, Administration Staff, Data Entry"
            },
        ],
        "training": [],
        "cv_tags": "Administration, Perbankan, Data Entry",
        "skills": {
            "hard": "Microsoft Office, Data Entry, Administrasi",
            "soft": "Detail Oriented, Teamwork",
            "lang": "Indonesian"
        }
    },
    {
        "first": "Rina", "last": "Amalia",
        "email": "rina.amalia@mail.com", "phone": "081234567025",
        "city": "Jakarta", "address": "Jl. Kemang Raya No. 12, Jakarta Selatan",
        "gender": "Perempuan", "dob": "2001-09-05", "is_fg": True, # Fresh Graduate
        "current_income": 0, "expected_income": 6000000, "available_from": "Immediately",
        "education": [
            {"inst": "Universitas Bina Nusantara", "major": "Teknik Informatika", "startyear": 2020, "endyear": 2024, "score": "3.72"},
        ],
        "experience": [],
        "training": [
            {"name": "React Developer Bootcamp", "cert": "REACT-2024"},
        ],
        "cv_tags": "IT, Web Development, React, Frontend",
        "skills": {
            "hard": "React, JavaScript, HTML, CSS, Tailwind",
            "soft": "Communication, Fast Learner",
            "lang": "Indonesian, English"
        }
    }
]

VACANCIES = [
    {
        "id": 1,
        "name": "Backend Engineer (Go/Python)",
        "desc": "Kami mencari Backend Engineer yang berpengalaman. Bertanggung jawab membangun API microservices.",
        "spec": "Pendidikan min S1 Teknik Informatika. Pengalaman min 2 tahun. Menguasai Go atau Python, Django, SQL. Nilai tambah jika memiliki sertifikasi AWS."
    },
    {
        "id": 2,
        "name": "Staff Administrasi",
        "desc": "Dibutuhkan staf administrasi umum untuk mengelola dokumen dan laporan bulanan.",
        "spec": "Pendidikan min D3/S1 semua jurusan. Mampu mengoperasikan Microsoft Excel dengan baik. Detail oriented."
    }
]


def seed():
    """Mengisi database development dengan data kandidat, lowongan, dan kualifikasi dummy."""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    print("  Clearing existing data for clean seed...")
    cur.execute("TRUNCATE apply_jobs, job_vacancy, candidate_tags, candidate_skills, candidate_experience_tags, requiretraining, requireworkexperience, requireeducation, require, users RESTART IDENTITY CASCADE;")

    # 1. Insert Vacancies
    print("  Seeding job_vacancy...")
    for v in VACANCIES:
        cur.execute(
            """INSERT INTO job_vacancy (job_vacancy_id, job_vacancy_name, job_vacancy_job_desc, job_vacancy_job_spec)
               VALUES (%s, %s, %s, %s)""",
            (v["id"], v["name"], v["desc"], v["spec"])
        )

    # 2. Insert Candidates & User Accounts
    print("  Seeding candidates and profiles...")
    for idx, c in enumerate(CANDIDATES, start=1):
        # Insert user
        cur.execute(
            """INSERT INTO users (id, name, email, role)
               VALUES (%s, %s, %s, 'candidate') RETURNING id""",
            (idx, f"{c['first']} {c['last']}", c["email"])
        )
        uid = cur.fetchone()[0]

        # Insert require
        cur.execute(
            """INSERT INTO require (firstname, lastname, gmail, phone, city, address, gender, dateofbirth, is_fresh_graduate, user_id, q14_current_income, q15_expected_income, q16_available_from, is_delete)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE) RETURNING requireid""",
            (c["first"], c["last"], c["email"], c["phone"], c["city"], c["address"], c["gender"], c["dob"], c["is_fg"], uid, c["current_income"], c["expected_income"], c["available_from"])
        )
        rid = cur.fetchone()[0]

        # Insert education
        for edu in c["education"]:
            cur.execute(
                """INSERT INTO requireeducation (requireid, institutionname, major, startyear, endyear, score, education_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (rid, edu["inst"], edu["major"], edu["startyear"], edu["endyear"], edu["score"], edu.get("level_id", 8))
            )

        # Insert work experience & experience tags
        for exp in c["experience"]:
            cur.execute(
                """INSERT INTO requireworkexperience (requireid, companyname, joblevel, jobdesk, startyear, endyear)
                   VALUES (%s, %s, %s, %s, %s, %s) RETURNING workid""",
                (rid, exp["company"], exp["joblevel"], exp["jobdesk"], exp["startyear"], exp["endyear"])
            )
            wid = cur.fetchone()[0]
            
            cur.execute(
                """INSERT INTO candidate_experience_tags (work_id, field_tag, role_tag, tags)
                   VALUES (%s, %s, %s, %s)""",
                (wid, exp["field_tag"], exp["role_tag"], exp["tags"])
            )

        # Insert training
        for t in c["training"]:
            cur.execute(
                """INSERT INTO requiretraining (requireid, trainingname, certificateno)
                   VALUES (%s, %s, %s)""",
                (rid, t["name"], t["cert"])
            )

        # Insert candidate_tags (precomputed)
        cur.execute(
            """INSERT INTO candidate_tags (require_id, tags)
               VALUES (%s, %s)""",
            (rid, c["cv_tags"])
        )

        # Insert candidate_skills (precomputed)
        cur.execute(
            """INSERT INTO candidate_skills (require_id, hard_skill, soft_skill, language)
               VALUES (%s, %s, %s, %s)""",
            (rid, c["skills"]["hard"], c["skills"]["soft"], c["skills"]["lang"])
        )

        # Apply for job 1 (Backend Position) for Andi and Siti
        if c["first"] in ("Andi", "Siti"):
            cur.execute(
                """INSERT INTO apply_jobs (job_vacancy_id, user_id)
                   VALUES (1, %s)""",
                (uid,)
            )
        # Apply for job 2 (Admin Position) for Budi
        elif c["first"] == "Budi":
            cur.execute(
                """INSERT INTO apply_jobs (job_vacancy_id, user_id)
                   VALUES (2, %s)""",
                (uid,)
            )

        print(f"  [OK] Berhasil memasukkan kandidat: {c['first']} {c['last']} (ID: {rid})")

    conn.commit()
    cur.close()
    conn.close()
    print("\n[SEED] Database seeding selesai dengan sukses!")


if __name__ == "__main__":
    seed()
