"""Unit dan integrasi test komprehensif (11 kasus uji) untuk logika pipa penyaringan kandidat."""

import os
import sys

# Tambahkan root folder ke PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.filtering.hard_filter import apply_hard_filters
from core.filtering.category_filter import check_category_compatibility
from core.filtering.taxonomy_matcher import match_job_role
from core.filtering.skills_filter import apply_skills_filter
from core.filtering.scoring import calculate_candidate_score
from core.filtering.skills_filter import build_candidate_skills
from app.services.filtering_service import adjust_score_by_tier


# ═══════════════════════════════════════════════════════════════
# REPRESENTASI KELAS MOCK UNTUK KANDIDAT & RIWAYAT (DATABASE MOCK)
# ═══════════════════════════════════════════════════════════════

class MockTags:
    def __init__(self, tags):
        self.tags = tags

class MockCandidateTags:
    def __init__(self, tags):
        self.tags = tags

class MockEducation:
    def __init__(self, major, education_id=3, score="3.50", institutionname="Universitas Metland"):
        self.education_id = education_id
        self.major = major
        self.score = score
        self.institutionname = institutionname
        self.startyear = 2016
        self.endyear = 2020

class MockExperience:
    def __init__(self, role_name, tags, companyname="PT Metland", jobdesk="", startyear=2020, endyear=2023, iscurrent=False):
        self.startdate = None
        self.enddate = None
        self.startyear = startyear
        self.endyear = endyear
        self.iscurrent = iscurrent
        self.jobdesk = jobdesk
        self.joblevel = role_name
        self.companyname = companyname
        self.experience_tags = MockTags(tags)

class MockTraining:
    def __init__(self, trainingname: str):
        self.trainingname = trainingname

class MockCandidateSkill:
    def __init__(self, hard_skill="", soft_skill="", language=""):
        self.hard_skill = hard_skill
        self.soft_skill = soft_skill
        self.language = language

class MockCandidate:
    def __init__(
        self,
        requireid,
        firstname,
        lastname,
        gender=None,
        dateofbirth=None,
        is_fresh_graduate=False,
        q16_available_from=None,
        q15_expected_income=None,
        educations=None,
        work_experiences=None,
        trainings=None,
        hard_skill=""
    ):
        self.requireid = requireid
        self.firstname = firstname
        self.lastname = lastname
        self.gender = gender
        self.dateofbirth = dateofbirth
        self.is_fresh_graduate = is_fresh_graduate
        self.q16_available_from = q16_available_from
        self.q15_expected_income = q15_expected_income
        self.educations = educations or []
        self.work_experiences = work_experiences or []
        self.trainings = trainings or []
        self.candidate_tags = MockCandidateTags("IT Support, Admin")
        self.candidate_skills = MockCandidateSkill(hard_skill=hard_skill)


# ═══════════════════════════════════════════════════════════════
# KELOMPOK PENGUJIAN INTEGRASI
# ═══════════════════════════════════════════════════════════════

def test_filtering_cases():
    print("\n--- Memulai Integrasi Test 11 Kasus Uji Filtering ---")

    # ---------------------------------------------------------------------------
    # TEST CASE 1: Batas Maksimum Pengalaman Kerja (Seniority Cap)
    # ---------------------------------------------------------------------------
    # Lowongan MT/Trainee: max_experience_years = 3.0
    # Pelamar memiliki pengalaman relevan = 5.0 tahun
    cand_1 = MockCandidate(
        requireid=1, firstname="Budi", lastname="Santoso",
        work_experiences=[
            MockExperience("Management Trainee", "HR & General Affairs, MT", startyear=2019, endyear=2024)
        ]
    )
    res_tax_1 = match_job_role(
        candidate_experiences=cand_1.work_experiences,
        job_title="Management Trainee",
        min_experience_years=0.0,
        max_experience_years=3.0,
        job_tags=["HR", "General Affairs"]
    )
    # Harus di-FAIL karena melebihi max_experience_years
    assert res_tax_1["decision"] == "FAIL"
    assert "melebihi batas maksimum" in res_tax_1["reason"]
    print("  [PASS] Test Case 1: Seniority Cap Berhasil!")

    # ---------------------------------------------------------------------------
    # TEST CASE 2: Bypass Lintas Bidang Entry-Level / Magang
    # ---------------------------------------------------------------------------
    # Lowongan Junior Web Developer: min_experience_years = 0.0
    # Kandidat: Fresh grad Hubungan Internasional (non-IT), skill Python (cocok dengan job_tags)
    cand_2 = MockCandidate(
        requireid=2, firstname="Siti", lastname="Aminah", is_fresh_graduate=True,
        educations=[MockEducation("Hubungan Internasional")],
        hard_skill="Python, Django"
    )
    res_tax_2 = match_job_role(
        candidate_experiences=cand_2.work_experiences,
        job_title="Junior Web Developer",
        min_experience_years=0.0,
        cv_tags_str="Python, Django",
        job_tags=["IT", "Web Development", "Python"],
        candidate_educations=cand_2.educations,
        is_fresh_graduate=True
    )
    # Fresh graduate dengan skill cocok di-upgrade ke PASS melalui "skills_match"
    assert res_tax_2["decision"] == "PASS"
    assert res_tax_2["match_type"] == "skills_match"
    print("  [PASS] Test Case 2: Bypass Lintas Bidang Entry-Level Berhasil!")

    # ---------------------------------------------------------------------------
    # TEST CASE 3: Proteksi Job Hopping Ekstrem
    # ---------------------------------------------------------------------------
    # Pelamar memiliki 4 posisi kerja berturut-turut, rata-rata durasi < 12 bulan
    cand_3 = MockCandidate(
        requireid=3, firstname="Rian", lastname="Hidayat",
        work_experiences=[
            MockExperience("Web Dev", "IT & Software, Web Developer", startyear=2020, endyear=2020), # ~12 bln
            MockExperience("Web Dev", "IT & Software, Web Developer", startyear=2021, endyear=2021),
            MockExperience("Web Dev", "IT & Software, Web Developer", startyear=2022, endyear=2022),
            MockExperience("Web Dev", "IT & Software, Web Developer", startyear=2023, endyear=2023)
        ]
    )
    # Simulasikan total durasi per posisi = 8 bulan
    # match_job_role menghitung total bulan menggunakan _calc_experience_months. 
    # Karena kita pakai startyear/endyear di mock, durasinya dihitung (end-start)*12.
    # Jika startyear=2020 dan endyear=2020, durasinya 0 bulan. Mari buat startyear/endyear yang menghasilkan total rata-rata < 12 bulan.
    # Di core/filtering/taxonomy/experience_evaluator.py:
    # _calc_experience_months menggunakan startdate/enddate, jika tidak ada fallback ke (endyear - startyear) * 12.
    # Jika startyear = 2020, endyear = 2020 -> durasi 0 bulan.
    # Mari kita masukkan startdate dan enddate agar kalkulasi bulannya akurat (misal: 6 bulan per posisi).
    from datetime import datetime
    exp_jh = [
        MockExperience("Web Dev", "IT & Software, Web Developer"),
        MockExperience("Web Dev", "IT & Software, Web Developer"),
        MockExperience("Web Dev", "IT & Software, Web Developer"),
        MockExperience("Web Dev", "IT & Software, Web Developer")
    ]
    for exp in exp_jh:
        exp.startdate = datetime(2020, 1, 1)
        exp.enddate = datetime(2020, 7, 1) # 6 bulan
    cand_3.work_experiences = exp_jh

    res_tax_3 = match_job_role(
        candidate_experiences=cand_3.work_experiences,
        job_title="Web Developer",
        min_experience_years=1.0,
        job_tags=["IT", "Web Development"]
    )
    # Harus diturunkan keputusannya ke UNKNOWN (REVIEW) akibat job hopping
    assert res_tax_3["decision"] == "UNKNOWN"
    assert "[Job Hopping]" in res_tax_3["reason"]
    print("  [PASS] Test Case 3: Proteksi Job Hopping Ekstrem Berhasil!")

    # ---------------------------------------------------------------------------
    # TEST CASE 4: Lolos Job Hopping Guard (Kandidat Stabil)
    # ---------------------------------------------------------------------------
    # Kandidat senior dengan 4 posisi berdurasi rata-rata 18 bulan
    exp_stable = [
        MockExperience("Web Dev", "IT & Software, Web Developer"),
        MockExperience("Web Dev", "IT & Software, Web Developer"),
        MockExperience("Web Dev", "IT & Software, Web Developer"),
        MockExperience("Web Dev", "IT & Software, Web Developer")
    ]
    for exp in exp_stable:
        exp.startdate = datetime(2020, 1, 1)
        exp.enddate = datetime(2021, 7, 1) # 18 bulan
    cand_4 = MockCandidate(requireid=4, firstname="Joko", lastname="Susilo", work_experiences=exp_stable)

    res_tax_4 = match_job_role(
        candidate_experiences=cand_4.work_experiences,
        job_title="Web Developer",
        min_experience_years=2.0,
        job_tags=["IT", "Web Development"]
    )
    # Harus lolos PASS karena rata-rata > 12 bulan (tidak dianggap job hopper)
    assert res_tax_4["decision"] == "PASS"
    print("  [PASS] Test Case 4: Lolos Job Hopping Guard Berhasil!")

    # ---------------------------------------------------------------------------
    # TEST CASE 5: Toleransi Peran Baru (PHP/Laravel vs Golang/NodeJS) & Degradasi Skor
    # ---------------------------------------------------------------------------
    # Lowongan PHP/Laravel, pelamar Web Developer (exact) tetapi keahlian Golang/NodeJS (no match)
    cand_5 = MockCandidate(
        requireid=5, firstname="Lia", lastname="Nirmala",
        work_experiences=[MockExperience("Web Developer", "IT & Software, Web Developer")],
        hard_skill="Golang, NodeJS"
    )
    req_5 = {"required_skills": ["PHP", "Laravel"]}
    tax_res_5 = {5: {"match_type": "exact", "reason": "Lolos peran"}}

    passed_5, eliminated_5 = apply_skills_filter(
        candidates=[cand_5],
        requirements=req_5,
        min_match_ratio=0.5,
        taxonomy_results=tax_res_5
    )
    # Lolos dari skills filter karena toleransi peran exact/related baru kita
    assert cand_5 in passed_5
    assert len(eliminated_5) == 0

    # Kalkulasi skor kasar dan penyesuaian tier
    # Karena tidak ada skill yang cocok, skor keahlian = 0.
    score_5, breakdown_5 = calculate_candidate_score(cand_5, req_5, {"match_type": "exact", "relevant_years": 3.0}, "Web Developer")
    
    # Karena required_skills ada tetapi matched = 0, di filtering_service.py statusnya diset REVIEW
    decision_status_5 = "REVIEW"
    adjusted_score_5 = adjust_score_by_tier(score_5, decision_status_5)
    
    # Asersi: skor disesuaikan masuk rentang REVIEW [30.0 - 49.9]
    assert 30.0 <= adjusted_score_5 <= 49.9
    print("  [PASS] Test Case 5: Toleransi Peran & Degradasi Skor Berhasil!")

    # ---------------------------------------------------------------------------
    # TEST CASE 6: Category Filter - Industri Tidak Kompatibel (Eliminasi Mutlak)
    # ---------------------------------------------------------------------------
    # Lowongan Finance Staff (kategori: Finance & Accounting)
    # Pelamar hanya punya pengalaman di bidang Food & Beverage
    cand_6 = MockCandidate(
        requireid=6, firstname="Siska", lastname="Amalia",
        work_experiences=[MockExperience("Pelayan Restoran", "Food & Beverage, Waiter")]
    )
    res_cat_6 = check_category_compatibility(
        candidate_experiences=cand_6.work_experiences,
        compatible_categories=["Finance & Accounting"]
    )
    # Harus di-FAIL/ELIMINATED
    assert res_cat_6["compatible"] is False
    assert "[Kategori Industri]" in res_cat_6["reason"]
    print("  [PASS] Test Case 6: Category Filter - Eliminasi Mutlak Berhasil!")

    # ---------------------------------------------------------------------------
    # TEST CASE 7: Pengecualian Category Filter (Benefit of the Doubt)
    # ---------------------------------------------------------------------------
    # Kandidat tidak memiliki data tag kategori industri sama sekali
    cand_7 = MockCandidate(
        requireid=7, firstname="Andi", lastname="Wijaya",
        work_experiences=[MockExperience("Karyawan", None)] # tags None
    )
    res_cat_7 = check_category_compatibility(
        candidate_experiences=cand_7.work_experiences,
        compatible_categories=["Finance & Accounting"]
    )
    # Harus diloloskan demi keamanan data kosong
    assert res_cat_7["compatible"] is True
    assert "Tidak ada data kategori" in res_cat_7["reason"]
    print("  [PASS] Test Case 7: Pengecualian Category Filter Berhasil!")

    # ---------------------------------------------------------------------------
    # TEST CASE 8: Smart Fallback Keahlian (Bila JD Tidak Memiliki Keahlian Wajib)
    # ---------------------------------------------------------------------------
    # Lowongan IT Support tanpa required_skills. Kandidat IT Support memiliki skill "Windows Server".
    # Sistem harus mengekstrak konteks dari judul posisi ("IT Support") secara semantik
    cand_8 = MockCandidate(
        requireid=8, firstname="Rudi", lastname="Hartono",
        hard_skill="Windows Server, Troubleshooting"
    )
    score_8, breakdown_8 = calculate_candidate_score(
        cand_8,
        requirements={"required_skills": [], "preferred_skills": []},
        taxonomy_result={"match_type": "exact", "relevant_years": 2.0},
        job_title="IT Support"
    )
    # Harus memanfaatkan Smart Fallback dan mendapatkan skor fungsional > 0
    assert breakdown_8["skills_match"]["score"] > 0
    assert "Smart Fallback used" in breakdown_8["skills_match"]["note"]
    print("  [PASS] Test Case 8: Smart Fallback Keahlian Berhasil!")

    # ---------------------------------------------------------------------------
    # TEST CASE 9: Bobot Adaptif Fresh Graduate di Skoring
    # ---------------------------------------------------------------------------
    # Kandidat A: Fresh Graduate, IPK 3.8, Pengalaman 0 tahun
    # Kandidat B: Profesional, IPK 2.5, Pengalaman 1 tahun
    cand_fg = MockCandidate(
        requireid=9, firstname="Andri", lastname="Setiawan", is_fresh_graduate=True,
        educations=[MockEducation("Teknik Informatika", score="3.80")]
    )
    cand_prof = MockCandidate(
        requireid=10, firstname="Eko", lastname="Prasetyo", is_fresh_graduate=False,
        educations=[MockEducation("Teknik Informatika", score="2.50")],
        work_experiences=[MockExperience("Junior Dev", "IT & Software, Web Developer", startyear=2022, endyear=2023)]
    )
    
    requirements_jr = {
        "min_experience_years": 0.0,
        "min_education": "S1",
        "required_skills": []
    }
    
    score_fg, breakdown_fg = calculate_candidate_score(cand_fg, requirements_jr, {"match_type": "no_experience", "relevant_years": 0.0}, "Junior Developer")
    score_prof, breakdown_prof = calculate_candidate_score(cand_prof, requirements_jr, {"match_type": "exact", "relevant_years": 1.0}, "Junior Developer")

    # Nilai IPK FG harus dikalikan pengali besar (2.4x) saat akumulasi skor
    assert breakdown_fg["fresh_graduate"] is True
    assert breakdown_prof["fresh_graduate"] is False
    assert breakdown_fg["gpa_score"]["score"] == 5.0 # Skor dasar mentah GPA
    assert score_fg == 39.0 # Total skor setelah dikalikan bobot adaptif
    print("  [PASS] Test Case 9: Bobot Adaptif Fresh Graduate Berhasil!")

    # ---------------------------------------------------------------------------
    # TEST CASE 10: Bonus Ketersediaan Bergabung Segera (Availability)
    # ---------------------------------------------------------------------------
    # Kandidat mencantumkan ketersediaan "segera bergabung" atau "ASAP"
    cand_10 = MockCandidate(
        requireid=11, firstname="Novi", lastname="Fitriani",
        q16_available_from="Immediately / Secepatnya"
    )
    score_10, breakdown_10 = calculate_candidate_score(
        cand_10,
        requirements={"min_experience_years": 0.0, "required_skills": []},
        taxonomy_result={"match_type": "exact", "relevant_years": 2.0},
        job_title="Staff Admin"
    )
    # Harus mendapat bonus ketersediaan +3.0 poin
    assert breakdown_10["available_soon"]["score"] == 3.0
    print("  [PASS] Test Case 10: Bonus Availability Berhasil!")

    # ---------------------------------------------------------------------------
    # TEST CASE 11: Bonus Industri Properti (Metland Specific)
    # ---------------------------------------------------------------------------
    # Kandidat memiliki riwayat kerja di perusahaan properti seperti Metland/Ciputra
    cand_11 = MockCandidate(
        requireid=12, firstname="Hendra", lastname="Gunawan",
        work_experiences=[
            MockExperience("Site Manager", "Engineering, Site Manager", companyname="PT Ciputra Development"),
            MockExperience("Supervisor", "Engineering, Supervisor", companyname="PT Metropolitan Land (Metland)")
        ]
    )
    # Aktifkan industry bonus melalui config import (atau asumsikan aktif)
    from app.config import settings
    settings.ENABLE_INDUSTRY_BONUS = True

    score_11, breakdown_11 = calculate_candidate_score(
        cand_11,
        requirements={"min_experience_years": 0.0, "required_skills": []},
        taxonomy_result={"match_type": "exact", "relevant_years": 5.0},
        job_title="Project Manager"
    )
    # Harus mendapat bonus industri properti (2.5 * 2 perusahaan = 5.0 poin)
    assert breakdown_11["industry_relevance"]["score"] == 5.0
    print("  [PASS] Test Case 11: Bonus Industri Properti Berhasil!")

    print("\n--- SELURUH 11 KASUS UJI INTEGRASI FILTERING BERHASIL! ---")


if __name__ == "__main__":
    test_filtering_cases()
