"""Utilitas untuk mengelola status pekerjaan aktif menggunakan Redis.

Menyediakan fungsi lock berbasis Redis agar aman digunakan pada
lingkungan web server dengan banyak worker proses.
"""

import logging
import redis
from app.config import settings

logger = logging.getLogger(__name__)


def get_redis_client() -> redis.Redis:
    """Mendapatkan instansi klien Redis dengan konfigurasi aplikasi.

    Return:
        redis.Redis: Klien Redis yang siap digunakan.
    """
    return redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD,
        decode_responses=True,
    )


def is_job_active(job_id: int) -> bool:
    """Memeriksa apakah suatu pekerjaan penyaringan sedang aktif berjalan.

    Parameter:
        job_id (int): ID lowongan pekerjaan (job_vacancy_id).

    Return:
        bool: True jika pekerjaan sedang aktif, False jika tidak.
    """
    try:
        r = get_redis_client()
        return bool(r.get(f"active_job:{job_id}"))
    except Exception as e:
        logger.error("Gagal memeriksa status pekerjaan aktif di Redis: %s", e)
        return False


def set_job_active(job_id: int, expire_seconds: int = 3600) -> None:
    """Menandai pekerjaan penyaringan sebagai aktif dengan masa kedaluwarsa.

    Parameter:
        job_id (int): ID lowongan pekerjaan (job_vacancy_id).
        expire_seconds (int): Waktu kedaluwarsa kunci dalam detik (default 3600).

    Return:
        None
    """
    try:
        r = get_redis_client()
        r.set(f"active_job:{job_id}", "1", ex=expire_seconds)
    except Exception as e:
        logger.error("Gagal menetapkan status pekerjaan aktif di Redis: %s", e)


def remove_job_active(job_id: int) -> None:
    """Menghapus status aktif pekerjaan penyaringan.

    Parameter:
        job_id (int): ID lowongan pekerjaan (job_vacancy_id).

    Return:
        None
    """
    try:
        r = get_redis_client()
        r.delete(f"active_job:{job_id}")
    except Exception as e:
        logger.error("Gagal menghapus status pekerjaan aktif di Redis: %s", e)
