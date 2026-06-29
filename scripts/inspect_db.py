"""Skrip inspeksi database untuk memvalidasi koneksi dan memeriksa struktur data tiruan/produksi."""

import os
import psycopg2
from dotenv import load_dotenv

# Muat variabel dari file .env
load_dotenv()

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "cvfiltering"),
    "user": os.getenv("DB_USER", "admin"),
    "password": os.getenv("DB_PASSWORD", "admin123"),
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": os.getenv("DB_PORT", "5433"),
}

def inspect_database():
    print("=" * 60)
    print("DIAGNOSTIK KONEKSI DATABASE")
    print("=" * 60)
    print(f"Host      : {DB_CONFIG['host']}")
    print(f"Port      : {DB_CONFIG['port']}")
    print(f"Database  : {DB_CONFIG['dbname']}")
    print(f"User      : {DB_CONFIG['user']}")
    print("-" * 60)

    try:
        # Hubungkan ke database
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print("[OK] Berhasil terhubung ke database.")
        print("-" * 60)

        # 1. Periksa Jumlah Lowongan Pekerjaan (job_vacancy)
        try:
            cursor.execute("SELECT COUNT(*) FROM job_vacancy;")
            total_jobs = cursor.fetchone()[0]
            print(f"Total Lowongan Kerja (job_vacancy) : {total_jobs} data")
            
            if total_jobs > 0:
                cursor.execute("SELECT job_vacancy_id, job_vacancy_name FROM job_vacancy LIMIT 5;")
                print("Sampel 5 lowongan teratas:")
                for job_id, name in cursor.fetchall():
                    print(f"  - ID: {job_id} | Nama: {name}")
        except Exception as e:
            print(f"[ERROR] Gagal membaca tabel job_vacancy: {e}")
        
        print("-" * 60)

        # 2. Periksa Jumlah Profil Kandidat (require)
        try:
            cursor.execute("SELECT COUNT(*) FROM require;")
            total_candidates = cursor.fetchone()[0]
            print(f"Total Profil Kandidat (require)    : {total_candidates} data")
            
            if total_candidates > 0:
                cursor.execute("SELECT requireid, firstname, lastname FROM require LIMIT 5;")
                print("Sampel 5 kandidat teratas:")
                for req_id, first, last in cursor.fetchall():
                    name = f"{first or ''} {last or ''}".strip()
                    print(f"  - ID: {req_id} | Nama: {name}")
        except Exception as e:
            print(f"[ERROR] Gagal membaca tabel require: {e}")
            
        print("-" * 60)

        # 3. Periksa Tabel Relasi & Cache CV Filtering
        tables = ["candidate_tags", "candidate_skills", "parsed_job_cache", "filtering_results"]
        print("Status Tabel Khusus CV-Filtering:")
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table};")
                count = cursor.fetchone()[0]
                print(f"  - {table:<25} : {count} data")
            except Exception as e:
                print(f"  - {table:<25} : [ERROR/TIDAK ADA] {e}")

        cursor.close()
        conn.close()

    except Exception as conn_err:
        print(f"[FATAL] Gagal menghubungkan ke database: {conn_err}")
        print("Silakan periksa apakah database aktif dan konfigurasi di .env sudah benar.")
    print("=" * 60)

if __name__ == "__main__":
    inspect_database()
