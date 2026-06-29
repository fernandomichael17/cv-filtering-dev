import sqlite3
import pickle
import os
import logging

logger = logging.getLogger(__name__)

class SQLiteCache:
    """
    Kelas pembantu untuk mengelola cache persisten menggunakan database SQLite lokal.
    Digunakan untuk menyimpan hasil embedding dan taksonomi yang mahal secara komputasi.
    """

    def __init__(self, db_path: str):
        """
        Inisialisasi SQLiteCache.

        Parameter:
            db_path (str): Jalur absolut/relatif ke file database SQLite.
        """
        self.db_path = os.path.normpath(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._memory_cache = {}
        self._init_db()

    def _init_db(self) -> None:
        """
        Membuat tabel cache jika belum ada di database SQLite.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value BLOB)"
                )
                conn.commit()
        except Exception as e:
            logger.error("Gagal menginisialisasi SQLite cache database: %s", e)

    def get(self, key: str) -> any:
        """
        Mengambil nilai dari cache berdasarkan kunci. Mencari di memory cache dahulu baru SQLite.

        Parameter:
            key (str): Kunci pencarian cache.

        Return:
            any: Nilai cache yang dide-serialisasi, atau None jika tidak ditemukan/error.
        """
        # Cek memory cache dahulu (sangat cepat)
        if key in self._memory_cache:
            return self._memory_cache[key]

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM cache WHERE key = ?", (key,))
                row = cursor.fetchone()
                if row:
                    val = pickle.loads(row[0])
                    # Simpan ke memory cache untuk lookup berikutnya
                    self._memory_cache[key] = val
                    return val
        except Exception as e:
            logger.warning("Gagal mengambil data dari cache untuk kunci %s: %s", key, e)
        return None

    def set(self, key: str, value: any) -> None:
        """
        Menyimpan atau memperbarui pasangan kunci-nilai di dalam cache (RAM & disk).

        Parameter:
            key (str): Kunci unik untuk data cache.
            value (any): Nilai data yang akan disimpan (serializable).
        """
        # Simpan ke memory cache
        self._memory_cache[key] = value

        try:
            val_bytes = pickle.dumps(value)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO cache (key, value) VALUES (?, ?)",
                    (key, val_bytes),
                )
                conn.commit()
        except Exception as e:
            logger.warning("Gagal menyimpan data ke cache untuk kunci %s: %s", key, e)
