"""Stress testing untuk mengevaluasi kepatuhan dan kemampuan LLM dalam parsing JD dan ekstraksi CV."""

import asyncio
import os
import sys
import json
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add root folder to PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.llm.jd_parser import parse_job_description
from core.llm.candidate_tagger import tag_candidate

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Mock database structures for Candidate Tagger
class MockEducation:
    def __init__(self, institutionname: str, major: str, score: str = "3.50"):
        self.institutionname = institutionname
        self.major = major
        self.score = score

class MockExperience:
    def __init__(self, workid: int, joblevel: str, jobdesk: str, companyname: str = "PT Metland"):
        self.workid = workid
        self.joblevel = joblevel
        self.jobdesk = jobdesk
        self.companyname = companyname
        self.startyear = 2021
        self.endyear = 2024

class MockCandidate:
    def __init__(self, requireid: int, firstname: str, lastname: str, educations=None, work_experiences=None):
        self.requireid = requireid
        self.firstname = firstname
        self.lastname = lastname
        self.educations = educations or []
        self.work_experiences = work_experiences or []
        self.trainings = []


# ═══════════════════════════════════════════════════════════════
# KASUS UJI JD PARSING (1 - 3)
# ═══════════════════════════════════════════════════════════════

# Test Case 1: Syarat Pendidikan Tersirat & Multi-Jurusan disingkat
JD_CASE_1 = """
Dibutuhkan Staff Finance & GA. 
Kualifikasi:
- Minimal lulusan D3/S1 Manajemen, Akuntansi, atau setara.
- IPK minimal 3.00 dari skala 4.00.
- Diutamakan yang memiliki sertifikat Brevet A & B.
"""

# Test Case 2: Kriteria Pengalaman & Keahlian yang digabungkan secara longgar
JD_CASE_2 = """
Mencari Mobile Developer. 
Syarat:
- Berpengalaman minimal 2 tahun mengembangkan aplikasi dengan React Native atau Flutter.
- Jika hanya menguasai salah satunya tidak apa-apa asal bersedia mempelajari yang lain.
"""

# Test Case 3: Kriteria Lokasi & Penempatan Terselubung
JD_CASE_3 = """
Posisi Site Supervisor Properti. 
Tanggung Jawab & Penempatan:
- Mengawasi jalannya proyek konstruksi bangunan di lapangan.
- Bersedia ditempatkan di proyek perumahan Metland Cileungsi, Metland Cibitung, atau proyek luar kota lainnya jika diperlukan.
"""


# ═══════════════════════════════════════════════════════════════
# KASUS UJI EKSTRAKSI KANDIDAT (4 - 5)
# ═══════════════════════════════════════════════════════════════

# Test Case 4: Pengalaman Kerja Bertumpuk / Rangkap Jabatan
CANDIDATE_CASE_4 = MockCandidate(
    requireid=204,
    firstname="Andi",
    lastname="Wijaya",
    educations=[MockEducation("Universitas Mercu Buana", "Sistem Informasi")],
    work_experiences=[
        MockExperience(
            workid=2004,
            joblevel="Staff Admin & IT Support",
            jobdesk="Di PT ABC saya menjabat sebagai Staff Admin sejak 2021, namun sejak pertengahan 2022 saya juga merangkap sebagai IT Support karena kekosongan staf. Tugas harian saya menginput data administrasi penjualan sekaligus melakukan troubleshooting jaringan kantor, setup PC karyawan baru, dan instalasi printer."
        )
    ]
)

# Test Case 5: Pengalaman Freelance / Proyek Mandiri tanpa Nama Perusahaan Resmi
CANDIDATE_CASE_5 = MockCandidate(
    requireid=205,
    firstname="Lia",
    lastname="Nirmala",
    educations=[MockEducation("Institut Kesenian Jakarta", "Desain Komunikasi Visual")],
    work_experiences=[
        MockExperience(
            workid=2005,
            joblevel="Freelance Content Designer",
            jobdesk="Bekerja mandiri (freelance) sebagai Pembuat Desain Konten Sosial Media sejak 2022. Mengelola akun Instagram klien properti, merancang aset visual dengan Canva, dan membuat copywriting promosi harian untuk menaikkan engagement."
        )
    ]
)


async def run_stress_tests():
    print("=" * 80)
    print("MEMULAI STRESS TEST KEMAMPUAN LLM (JD PARSING & CANDIDATE EXTRACTION)")
    print("=" * 80)

    passed_tests = 0
    failed_tests = 0

    # ---------------------------------------------------------------------------
    # UJI COBA 1: Staff Finance & GA
    # ---------------------------------------------------------------------------
    print("\n[TEST 1] JD Parsing: Staff Finance & GA (Pendidikan D3/S1 & Brevet)")
    try:
        res1 = await parse_job_description(JD_CASE_1)
        print("  -> Output JSON:", json.dumps(res1, indent=2, ensure_ascii=False))
        
        # Validasi asersi
        assert res1.get("min_education") == "D3", f"Expected D3, got {res1.get('min_education')}"
        assert any("Manajemen" in m for m in res1.get("allowed_majors", [])), "Allowed majors should include Manajemen"
        assert any("Akuntansi" in m for m in res1.get("allowed_majors", [])), "Allowed majors should include Akuntansi"
        assert res1.get("min_gpa") == 3.0, f"Expected GPA 3.0, got {res1.get('min_gpa')}"
        
        print("  [PASS] Test 1 Berhasil!")
        passed_tests += 1
    except AssertionError as ae:
        print("  [FAIL] Test 1 Gagal pada Asersi:", ae)
        failed_tests += 1
    except Exception as e:
        print("  [ERROR] Test 1 Error:", e)
        failed_tests += 1

    # ---------------------------------------------------------------------------
    # UJI COBA 2: Mobile Developer
    # ---------------------------------------------------------------------------
    print("\n[TEST 2] JD Parsing: Mobile Developer (React Native atau Flutter)")
    try:
        res2 = await parse_job_description(JD_CASE_2)
        print("  -> Output JSON:", json.dumps(res2, indent=2, ensure_ascii=False))
        
        assert res2.get("min_experience_years") == 2, f"Expected 2 years, got {res2.get('min_experience_years')}"
        skills = [s.lower() for s in res2.get("required_skills", []) + res2.get("preferred_skills", [])]
        assert any("react native" in s for s in skills), "Skills should contain React Native"
        assert any("flutter" in s for s in skills), "Skills should contain Flutter"
        
        print("  [PASS] Test 2 Berhasil!")
        passed_tests += 1
    except AssertionError as ae:
        print("  [FAIL] Test 2 Gagal pada Asersi:", ae)
        failed_tests += 1
    except Exception as e:
        print("  [ERROR] Test 2 Error:", e)
        failed_tests += 1

    # ---------------------------------------------------------------------------
    # UJI COBA 3: Site Supervisor Properti (Penempatan Luar Kota)
    # ---------------------------------------------------------------------------
    print("\n[TEST 3] JD Parsing: Site Supervisor Properti (Penempatan Luar Jakarta)")
    try:
        res3 = await parse_job_description(JD_CASE_3)
        print("  -> Output JSON:", json.dumps(res3, indent=2, ensure_ascii=False))
        
        assert res3.get("placement_outside_jakarta") is True, "Expected placement_outside_jakarta to be True due to 'luar kota'"
        
        print("  [PASS] Test 3 Berhasil!")
        passed_tests += 1
    except AssertionError as ae:
        print("  [FAIL] Test 3 Gagal pada Asersi:", ae)
        failed_tests += 1
    except Exception as e:
        print("  [ERROR] Test 3 Error:", e)
        failed_tests += 1

    # ---------------------------------------------------------------------------
    # UJI COBA 4: Candidate Tagger - Rangkap Jabatan
    # ---------------------------------------------------------------------------
    print("\n[TEST 4] Candidate Tagger: Staff Admin & IT Support (Rangkap)")
    try:
        res4 = await tag_candidate(CANDIDATE_CASE_4)
        print("  -> Output JSON:", json.dumps(res4, indent=2, ensure_ascii=False))
        
        hard_skills_lower = (res4.get("skills", {}).get("hard_skill") or "").lower()
        cv_tags_lower = (res4.get("cv_tags") or "").lower()
        
        # Validasi ada unsur IT support/troubleshooting sekaligus admin/data entry
        has_it = any(w in hard_skills_lower or w in cv_tags_lower for w in ["it support", "network", "jaringan", "troubleshooting", "setup pc"])
        has_admin = any(w in hard_skills_lower or w in cv_tags_lower for w in ["admin", "data entry", "input data"])
        
        assert has_it, f"Should extract IT Support / Networking skills, got: {hard_skills_lower}"
        assert has_admin, f"Should extract Admin / Data Entry skills, got: {hard_skills_lower}"
        
        print("  [PASS] Test 4 Berhasil!")
        passed_tests += 1
    except AssertionError as ae:
        print("  [FAIL] Test 4 Gagal pada Asersi:", ae)
        failed_tests += 1
    except Exception as e:
        print("  [ERROR] Test 4 Error:", e)
        failed_tests += 1

    # ---------------------------------------------------------------------------
    # UJI COBA 5: Candidate Tagger - Freelance Content Designer
    # ---------------------------------------------------------------------------
    print("\n[TEST 5] Candidate Tagger: Freelance Content Designer (Canva & Copywriting)")
    try:
        res5 = await tag_candidate(CANDIDATE_CASE_5)
        print("  -> Output JSON:", json.dumps(res5, indent=2, ensure_ascii=False))
        
        hard_skills_lower = (res5.get("skills", {}).get("hard_skill") or "").lower()
        cv_tags_lower = (res5.get("cv_tags") or "").lower()
        
        has_canva = "canva" in hard_skills_lower or "canva" in cv_tags_lower
        has_copywriting = "copywriting" in hard_skills_lower or "copywriting" in cv_tags_lower
        has_social = any(w in hard_skills_lower or w in cv_tags_lower for w in ["social media", "sosial media", "design", "desain"])
        
        assert has_canva, f"Should extract Canva, got: {hard_skills_lower}"
        assert has_copywriting, f"Should extract Copywriting, got: {hard_skills_lower}"
        assert has_social, f"Should extract Social Media Design, got: {hard_skills_lower}"
        
        print("  [PASS] Test 5 Berhasil!")
        passed_tests += 1
    except AssertionError as ae:
        print("  [FAIL] Test 5 Gagal pada Asersi:", ae)
        failed_tests += 1
    except Exception as e:
        print("  [ERROR] Test 5 Error:", e)
        failed_tests += 1

    # ---------------------------------------------------------------------------
    # RINGKASAN AKHIR
    # ---------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print(f"STRESS TEST SELESAI: {passed_tests} PASSED, {failed_tests} FAILED / ERROR")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_stress_tests())
