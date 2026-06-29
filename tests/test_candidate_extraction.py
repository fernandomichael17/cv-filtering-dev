"""Uji coba langsung kemampuan ekstraksi tag/keahlian kandidat menggunakan LLM.

Menjalankan ekstraksi asinkron untuk 5 kandidat dengan latar belakang profesi berbeda,
di mana deskripsi pengalaman kerja tidak menyebutkan tools/teknologi secara spesifik,
untuk menguji kecerdasan LLM dalam mengenali keahlian fungsional secara implisit.
"""

import asyncio
import os
import json
import logging
from dotenv import load_dotenv

# Konfigurasi Logging sederhana
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables dari berkas .env
load_dotenv()

# Tambahkan cwd ke PYTHONPATH agar bisa impor modul core/app
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.llm.candidate_tagger import tag_candidate

# ═══════════════════════════════════════════════════════════════
# Representasi Kelas Mock untuk Objek Database Require
# ═══════════════════════════════════════════════════════════════

class MockEducation:
    def __init__(self, institutionname: str, major: str, score: str = "3.50"):
        self.institutionname = institutionname
        self.major = major
        self.score = score

class MockExperience:
    def __init__(self, workid: int, joblevel: str, jobdesk: str, companyname: str = "PT Uji Coba"):
        self.workid = workid
        self.joblevel = joblevel
        self.jobdesk = jobdesk
        self.companyname = companyname
        self.startyear = 2020
        self.endyear = 2024

class MockTraining:
    def __init__(self, trainingname: str):
        self.trainingname = trainingname

class MockCandidate:
    def __init__(
        self,
        requireid: int,
        firstname: str,
        lastname: str,
        educations=None,
        work_experiences=None,
        trainings=None
    ):
        self.requireid = requireid
        self.firstname = firstname
        self.lastname = lastname
        self.educations = educations or []
        self.work_experiences = work_experiences or []
        self.trainings = trainings or []

# ═══════════════════════════════════════════════════════════════
# Pembuatan Data 5 Kandidat Uji Coba Lintas Profesi
# ═══════════════════════════════════════════════════════════════

candidates = [
    # Kandidat 1: HRGA / Industrial Relations (Deskripsi Fungsional)
    MockCandidate(
        requireid=101,
        firstname="Dewi",
        lastname="Lestari",
        educations=[MockEducation("Universitas Indonesia", "Psikologi")],
        work_experiences=[
            MockExperience(
                workid=1001,
                joblevel="HR Generalist",
                jobdesk="Mengelola proses rekrutmen karyawan baru dari penyaringan berkas hingga wawancara akhir. Menangani kasus perselisihan hubungan industrial antara karyawan dan manajemen perusahaan. Memastikan kepatuhan seluruh kebijakan operasional kantor terhadap regulasi ketenagakerjaan pemerintah, serta mengelola kompensasi bulanan dan administrasi data karyawan."
            )
        ]
    ),
    
    # Kandidat 2: Akuntansi / Perpajakan (Tanpa Menyebut accurate/Excel)
    MockCandidate(
        requireid=102,
        firstname="Bambang",
        lastname="Pamungkas",
        educations=[MockEducation("Universitas Padjadjaran", "Akuntansi")],
        work_experiences=[
            MockExperience(
                workid=1002,
                joblevel="Staff Accounting & Tax",
                jobdesk="Menyusun laporan keuangan bulanan dan tahunan perusahaan untuk keperluan rapat manajemen. Mencatat setiap transaksi keuangan ke dalam buku besar secara rapi. Menghitung, menyetorkan, dan melaporkan kewajiban perpajakan badan bulanan, serta melakukan rekonsiliasi kas bank harian."
            )
        ]
    ),
    
    # Kandidat 3: Front-End UI Developer (Tanpa menyebut React/Vue)
    MockCandidate(
        requireid=103,
        firstname="Rian",
        lastname="Hidayat",
        educations=[MockEducation("Institut Teknologi Bandung", "Teknik Informatika")],
        work_experiences=[
            MockExperience(
                workid=1003,
                joblevel="Front End Developer",
                jobdesk="Membangun antarmuka web yang interaktif dan responsif untuk berbagai ukuran layar pengguna. Merancang pustaka komponen visual yang konsisten guna mempercepat proses pembuatan halaman. Menghubungkan halaman web depan dengan layanan RESTful API yang disediakan oleh tim backend."
            )
        ]
    ),
    
    # Kandidat 4: Sales Executive / Negosiator (Tanpa menyebut Brand CRM)
    MockCandidate(
        requireid=104,
        firstname="Siska",
        lastname="Amalia",
        educations=[MockEducation("Universitas Gadjah Mada", "Ilmu Komunikasi")],
        work_experiences=[
            MockExperience(
                workid=1004,
                joblevel="Sales Executive",
                jobdesk="Mencari prospek klien baru secara aktif melalui telepon maupun kunjungan langsung. Melakukan presentasi produk secara persuasif ke calon pembeli korporat. Menegosiasikan harga dan kesepakatan kontrak penjualan untuk mencapai kesepakatan terbaik, serta memelihara hubungan baik dengan pelanggan lama guna mencapai target omzet bulanan."
            )
        ]
    ),
    
    # Kandidat 5: Teknik Sipil / Struktur (Tanpa menyebut AutoCAD/SAP2000)
    MockCandidate(
        requireid=105,
        firstname="Joko",
        lastname="Susilo",
        educations=[MockEducation("Universitas Diponegoro", "Teknik Sipil")],
        work_experiences=[
            MockExperience(
                workid=1005,
                joblevel="Civil Engineer",
                jobdesk="Merancang gambar cetak biru konstruksi gedung bertingkat tinggi secara detail. Menghitung kekuatan beban struktur bangunan serta ketahanan beton dan baja terhadap gempa. Melakukan pengawasan langsung di lapangan untuk memastikan kualitas pengecoran dan pengerjaan kontraktor sesuai standar keselamatan sipil."
            )
        ]
    )
]

# ═══════════════════════════════════════════════════════════════
# Fungsi Utama Eksekusi Uji Coba Ekstraksi
# ═══════════════════════════════════════════════════════════════

async def run_tests():
    print("=" * 70)
    print("MEMULAI EVALUASI EKSTRAKSI KANDIDAT LINTAS PROFESI (IMPLICIT SKILLS)")
    print("=" * 70)
    
    for cand in candidates:
        print(f"\n[Kandidat #{cand.requireid}] {cand.firstname} {cand.lastname}")
        print(f"  Jurusan: {cand.educations[0].major}")
        print(f"  Deskripsi Kerja: {cand.work_experiences[0].jobdesk[:120]}...")
        
        try:
            # Panggil fungsi asinkron LLM tag_candidate
            result = await tag_candidate(cand)
            
            print("  -> HASIL EKSTRAKSI:")
            print(f"     * CV Tags      : {result.get('cv_tags')}")
            print(f"     * Hard Skills  : {result.get('skills', {}).get('hard_skill')}")
            print(f"     * Soft Skills  : {result.get('skills', {}).get('soft_skill')}")
            print(f"     * Experience   : {json.dumps(result.get('experience_tags'), ensure_ascii=False)}")
            
        except Exception as e:
            print(f"  [GAGAL] Terjadi error saat ekstraksi: {e}")
        print("-" * 70)

if __name__ == "__main__":
    asyncio.run(run_tests())
