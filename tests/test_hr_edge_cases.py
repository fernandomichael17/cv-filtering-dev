"""
Skenario Pengujian Edge Cases HR Indonesia.
Berfokus pada anomali CV dan Job Description yang sering ditemui di lapangan:
1. Ekstraksi Pengalaman Pecahan (0.5 Tahun)
2. Keahlian Typo / Akronim
3. Generalist Role (Jabatan campur aduk)
4. Overqualified (Pendidikan lebih tinggi dari syarat minimal)
5. Lifetime Employed (Pengalaman kerja tanpa end_year)
"""
import pytest
from datetime import datetime
from unittest.mock import MagicMock

# Import modul yang diuji
from core.filtering.hard_filter import apply_hard_filters, _get_total_experience_years
from core.filtering.semantic_matcher import semantic_matcher, SemanticTaxonomyMatcher
from core.utils.skill_synonyms import get_skill_synonyms
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
        self.startdate = None
        self.enddate = None
        self.iscurrent = False

class MockCandidate:
    def __init__(self, requireid: int, work_experiences: list = None, educations: list = None):
        self.requireid = requireid
        self.firstname = f"Kandidat"
        self.lastname = str(requireid)
        self.work_experiences = work_experiences or []
        self.educations = educations or []
        self.gender = "L"
        self.age = 25
        self.maritalstatus = "Belum Kawin"

# --- KASUS 1: Pengalaman 6 Bulan vs Syarat 1 Tahun ---
def test_fractional_experience_months():
    # Syarat: Minimal 1 Tahun (1.0)
    requirements = {"min_experience_years": 1.0}
    
    # Kandidat 1: Bekerja dengan start_date & end_date persis 6 bulan (sekitar 180 hari)
    exp1 = MockExperience(workid=1, joblevel="Staff", jobdesk="Admin")
    exp1.startdate = datetime(2023, 1, 1)
    exp1.enddate = datetime(2023, 7, 1) # 181 days ~ 6 months
    
    # Berikan edu minimal agar tidak tereliminasi karena Pendidikan
    edu1 = MockEducation("Univ A", "IT", score="3.0")
    edu1.education_id = 4 # 4 = SMA
    c1 = MockCandidate(requireid=101, work_experiences=[exp1], educations=[edu1])
    
    # Kalkulasi pengalaman
    exp_years = _get_total_experience_years([exp1])
    assert 0.4 <= exp_years <= 0.6  # Harus berkisar 0.5 tahun
    
    # Filter test
    passed, eliminated = apply_hard_filters([c1], requirements)
    assert len(passed) == 0
    assert len(eliminated) == 1
    assert "Masa Kerja" in eliminated[0]["reason"]

# --- KASUS 2: Keahlian Typo / Akronim ---
def test_skill_synonyms_typo():
    # Memastikan sinonim bisa mendeteksi kata-kata singkatan HR
    assert "js" in [s.lower() for s in get_skill_synonyms("JavaScript")]
    assert "golang" in [s.lower() for s in get_skill_synonyms("Go")]
    assert "excel" in [s.lower() for s in get_skill_synonyms("Microsoft Excel")]

# --- KASUS 3: Generalist Role (Jabatan campur aduk) ---
@pytest.mark.asyncio
async def test_generalist_role_taxonomy():
    matcher = SemanticTaxonomyMatcher()
    matcher.is_initialized = True
    
    mock_sqlite = MagicMock()
    mock_sqlite.get.return_value = None
    matcher._db_cache = mock_sqlite
    
    # Mocking model NLP agar tidak men-download model saat test berjalan
    mock_model = MagicMock()
    # Dummy embedding (akan menyebabkan cosine similarity tinggi atau rendah tergantung jarak, 
    # tapi kita tidak bisa mensimulasikan vektor secara persis di test ini tanpa model asli).
    # Namun kita bisa memastikan fungsinya tidak error saat diberikan string campur aduk.
    matcher.model = mock_model
    mock_model.encode.return_value = [[0.1, 0.2]]
    
    # Ini harusnya memanggil get_embedding tanpa crash, sekalipun panjang
    emb = matcher.get_embedding("IT Support / Admin GA / Customer Service / Social Media")
    assert emb is not None

# --- KASUS 4: Overqualified (Pendidikan lebih tinggi) ---
def test_overqualified_education():
    # JD meminta minimum D3
    requirements = {"min_education": "D3"}
    
    # Kandidat adalah S2 (Magister)
    c1 = MockCandidate(requireid=201)
    c1.educations = [MockEducation("Univ B", "Bisnis", score="3.50")]
    c1.educations[0].education_id = 7 # Misal 7 = S2 / Master
    
    # Harus lolos karena S2 >= D3
    passed, eliminated = apply_hard_filters([c1], requirements)
    assert len(passed) == 1

# --- KASUS 5: Lifetime Employed (Pengalaman kerja tanpa end_year) ---
def test_lifetime_employed_experience():
    # Kandidat mulai 2020, tapi iscurrent=True (masih bekerja sampai sekarang)
    exp1 = MockExperience(workid=2, joblevel="Senior", jobdesk="Dev")
    exp1.startyear = 2020
    exp1.endyear = None
    exp1.iscurrent = True
    
    exp_years = _get_total_experience_years([exp1])
    current_year = datetime.now().year
    expected_min = current_year - 2020 - 1  # Toleransi bawah (awal tahun)
    expected_max = current_year - 2020 + 1  # Toleransi atas
    
    assert expected_min <= exp_years <= expected_max

# --- KASUS 6: Overlap Pengalaman Kerja (Timeline Merge) ---
def test_overlapping_experience_not_double_counted():
    """Kandidat bekerja di 2 tempat bersamaan: 2020-2023 & 2021-2024. Harus 4 tahun, bukan 7."""
    exp1 = MockExperience(workid=1, joblevel="Staff", jobdesk="Dev")
    exp1.startdate = datetime(2020, 1, 1)
    exp1.enddate = datetime(2023, 1, 1)
    
    exp2 = MockExperience(workid=2, joblevel="Staff", jobdesk="QA")
    exp2.startdate = datetime(2021, 1, 1)
    exp2.enddate = datetime(2024, 1, 1)
    
    exp_years = _get_total_experience_years([exp1, exp2])
    # Seharusnya 4 tahun (2020-01-01 s/d 2024-01-01), bukan 6 tahun (3+3)
    assert 3.9 <= exp_years <= 4.1

def test_non_overlapping_experience_summed():
    """Dua pengalaman berurutan tanpa overlap: 2018-2020 & 2021-2023. Harus 4 tahun."""
    exp1 = MockExperience(workid=1, joblevel="Staff", jobdesk="Dev")
    exp1.startdate = datetime(2018, 1, 1)
    exp1.enddate = datetime(2020, 1, 1)
    
    exp2 = MockExperience(workid=2, joblevel="Staff", jobdesk="QA")
    exp2.startdate = datetime(2021, 1, 1)
    exp2.enddate = datetime(2023, 1, 1)
    
    exp_years = _get_total_experience_years([exp1, exp2])
    # 2 + 2 = 4 tahun (tidak ada overlap)
    assert 3.9 <= exp_years <= 4.1

def test_fully_contained_experience():
    """Pengalaman B sepenuhnya di dalam pengalaman A: A=2019-2025, B=2020-2022. Harus 6 tahun."""
    exp1 = MockExperience(workid=1, joblevel="Manager", jobdesk="Management")
    exp1.startdate = datetime(2019, 1, 1)
    exp1.enddate = datetime(2025, 1, 1)
    
    exp2 = MockExperience(workid=2, joblevel="Staff", jobdesk="Freelance")
    exp2.startdate = datetime(2020, 1, 1)
    exp2.enddate = datetime(2022, 1, 1)
    
    exp_years = _get_total_experience_years([exp1, exp2])
    # B sepenuhnya di dalam A, jadi total tetap 6 tahun
    assert 5.9 <= exp_years <= 6.1

