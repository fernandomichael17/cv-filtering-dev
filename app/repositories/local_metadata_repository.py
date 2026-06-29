"""Repository untuk mengelola penyimpanan metadata analitik AI ke database SQLite lokal terpisah."""

import os
import sqlite3
import json
import logging

logger = logging.getLogger(__name__)

DB_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', 'data'))
DB_PATH = os.path.join(DB_DIR, 'filtering_metadata.db')

class LocalMetadataRepository:
    """Mengelola database SQLite lokal khusus untuk metadata analitik AI (confidence, score, breakdown)."""

    def __init__(self):
        """Inisialisasi repository dan membuat tabel jika belum ada."""
        os.makedirs(DB_DIR, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Membuat tabel candidate_metadata di SQLite database lokal jika belum tersedia."""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS candidate_metadata (
                        job_vacancy_id INTEGER,
                        require_id INTEGER,
                        confidence TEXT,
                        total_score REAL,
                        score_breakdown TEXT,
                        PRIMARY KEY (job_vacancy_id, require_id)
                    )
                    """
                )
                conn.commit()
        except Exception as e:
            logger.error("Gagal menginisialisasi SQLite metadata database: %s", e)

    def save_metadata_bulk(self, job_vacancy_id: int, metadata_list: list[dict]) -> None:
        """Menyimpan data metadata secara massal untuk satu lowongan pekerjaan menggunakan satu transaksi.

        Parameter:
            job_vacancy_id (int): ID lowongan pekerjaan.
            metadata_list (list[dict]): Daftar metadata kandidat (require_id, confidence, total_score, score_breakdown).

        Return:
            None
        """
        if not metadata_list:
            return

        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                # Siapkan data untuk query insert/replace
                insert_data = []
                for item in metadata_list:
                    req_id = item.get("require_id")
                    conf = item.get("confidence", "")
                    score = item.get("total_score", 0.0)
                    breakdown_str = json.dumps(item.get("score_breakdown", {}))
                    insert_data.append((job_vacancy_id, req_id, conf, score, breakdown_str))

                cursor.executemany(
                    """
                    INSERT OR REPLACE INTO candidate_metadata 
                    (job_vacancy_id, require_id, confidence, total_score, score_breakdown)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    insert_data
                )
                conn.commit()
                logger.info("Berhasil menyimpan %d metadata kandidat ke SQLite lokal.", len(metadata_list))
        except Exception as e:
            logger.error("Gagal menyimpan metadata kandidat secara massal ke SQLite: %s", e)

    def get_metadata_by_job_id(self, job_vacancy_id: int) -> dict[int, dict]:
        """Mengambil seluruh data metadata kandidat untuk ID lowongan tertentu dari SQLite lokal.

        Parameter:
            job_vacancy_id (int): ID lowongan pekerjaan.

        Return:
            dict[int, dict]: Mapping require_id ke dictionary berisi confidence, total_score, dan score_breakdown.
        """
        results_map = {}
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT require_id, confidence, total_score, score_breakdown 
                    FROM candidate_metadata 
                    WHERE job_vacancy_id = ?
                    """,
                    (job_vacancy_id,)
                )
                rows = cursor.fetchall()
                for row in rows:
                    req_id, conf, score, breakdown_str = row
                    breakdown = {}
                    if breakdown_str:
                        try:
                            breakdown = json.loads(breakdown_str)
                        except json.JSONDecodeError:
                            pass
                    results_map[req_id] = {
                        "confidence": conf,
                        "total_score": score,
                        "score_breakdown": breakdown
                    }
        except Exception as e:
            logger.error("Gagal mengambil metadata dari SQLite lokal untuk Job #%d: %s", job_vacancy_id, e)
        return results_map

    def delete_metadata_by_job_id(self, job_vacancy_id: int) -> None:
        """Menghapus seluruh metadata kandidat untuk ID lowongan tertentu dari SQLite lokal.

        Parameter:
            job_vacancy_id (int): ID lowongan pekerjaan yang akan dibersihkan.

        Return:
            None
        """
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    "DELETE FROM candidate_metadata WHERE job_vacancy_id = ?",
                    (job_vacancy_id,)
                )
                conn.commit()
                logger.info("Metadata lama untuk Job #%d berhasil dihapus dari SQLite.", job_vacancy_id)
        except Exception as e:
            logger.error("Gagal menghapus metadata dari SQLite lokal untuk Job #%d: %s", job_vacancy_id, e)

    def delete_metadata_by_candidate_id(self, require_id: int) -> None:
        """Menghapus seluruh metadata untuk ID kandidat tertentu (require_id) dari seluruh lowongan di SQLite lokal.

        Parameter:
            require_id (int): ID kandidat yang akan dibersihkan.

        Return:
            None
        """
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    "DELETE FROM candidate_metadata WHERE require_id = ?",
                    (require_id,)
                )
                conn.commit()
                logger.info("Metadata lama untuk Kandidat #%d berhasil dihapus dari SQLite.", require_id)
        except Exception as e:
            logger.error("Gagal menghapus metadata dari SQLite lokal untuk Kandidat #%d: %s", require_id, e)
