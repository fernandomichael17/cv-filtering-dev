"""Script untuk melakukan drop tabel filtering_results di PostgreSQL agar kolom baru dapat dibuat otomatis pada startup berikutnya."""

import asyncio
import os
import sys

# Tambahkan root folder ke PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text
from app.database import engine

async def reset_table():
    print("Menghapus tabel filtering_results di PostgreSQL...")
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS filtering_results CASCADE;"))
    print("Tabel berhasil dihapus. Restart kontainer FastAPI untuk membuat ulang skema baru.")

if __name__ == "__main__":
    asyncio.run(reset_table())
