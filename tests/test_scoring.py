"""Unit test untuk komponen scoring di CV Filtering v2.

Menguji fungsi-fungsi perhitungan skor seperti available soon, income fit,
sertifikasi, serta pembobotan skor akhir kandidat.
"""

import pytest
from core.filtering.scoring import (
    _score_available_soon,
    _score_income_fit,
    calculate_candidate_score,
    _score_certifications,
    _match_cert_for_scoring,
)

class MockEducation:
    """Mock kelas untuk riwayat pendidikan kandidat."""
    def __init__(self, score, major):
        self.score = score
        self.major = major
        self.institutionname = "Mock University"
        self.startyear = 2018
        self.endyear = 2022


class MockWorkExperience:
    """Mock kelas untuk riwayat pengalaman kerja kandidat."""
    def __init__(self, companyname, joblevel, jobdesk, startyear, endyear, iscurrent=False):
        self.companyname = companyname
        self.joblevel = joblevel
        self.jobdesk = jobdesk
        self.startyear = startyear
        self.endyear = endyear
        self.iscurrent = iscurrent
        self.startdate = None
        self.enddate = None
        self.experience_tags = None


class MockCandidate:
    """Mock kelas utama untuk entitas kandidat (Require)."""
    def __init__(self, is_fresh_graduate=False, q16_available_from=None, q15_expected_income=None):
        self.firstname = "Budi"
        self.lastname = "Santoso"
        self.requireid = 1
        self.is_fresh_graduate = is_fresh_graduate
        self.q16_available_from = q16_available_from
        self.q15_expected_income = q15_expected_income
        self.educations = []
        self.work_experiences = []
        self.trainings = []
        self.candidate_tags = None
        self.candidate_skills = None


class MockTraining:
    """Mock kelas untuk data sertifikasi/pelatihan kandidat."""
    def __init__(self, name):
        self.trainingname = name


def test_score_available_soon():
    """
    Menguji fungsi _score_available_soon dengan berbagai variasi ketersediaan kandidat.
    """
    # Kasus 1: Segera bergabung
    candidate_1 = MockCandidate(q16_available_from="Immediately")
    score, detail = _score_available_soon(candidate_1)
    assert score == 3.0
    assert detail["score"] == 3.0

    # Kasus 2: 1 bulan lagi
    candidate_2 = MockCandidate(q16_available_from="1 month")
    score, detail = _score_available_soon(candidate_2)
    assert score == 3.0

    # Kasus 3: Ketersediaan kosong
    candidate_3 = MockCandidate(q16_available_from=None)
    score, detail = _score_available_soon(candidate_3)
    assert score == 0.0


def test_score_income_fit():
    """
    Menguji fungsi _score_income_fit dengan mencocokkan ekspektasi gaji terhadap budget lowongan.
    """
    requirements = {"budget": 10000000}

    # Kasus 1: Ekspektasi gaji di bawah budget
    candidate_1 = MockCandidate(q15_expected_income=8000000)
    score, detail = _score_income_fit(candidate_1, requirements)
    assert score == 2.0
    assert detail["score"] == 2.0

    # Kasus 2: Ekspektasi gaji di atas budget
    candidate_2 = MockCandidate(q15_expected_income=12000000)
    score, detail = _score_income_fit(candidate_2, requirements)
    assert score == 0.0

    # Kasus 3: Ekspektasi gaji atau budget tidak didefinisikan
    candidate_3 = MockCandidate(q15_expected_income=None)
    score, detail = _score_income_fit(candidate_3, requirements)
    assert score == 0.0


def test_score_certifications(monkeypatch):
    """
    Menguji perhitungan skor sertifikasi dengan threshold baru (0.80 untuk required & 0.65 untuk bonus).
    """
    import core.filtering.scoring as scoring_module
    
    # Mocking semantic_matcher agar tidak memuat model transformer yang berat secara langsung
    mock_sim = 0.0
    def mock_calculate_max_similarity(query, targets):
        return mock_sim, targets[0] if targets else ""
        
    monkeypatch.setattr(scoring_module.semantic_matcher, "calculate_max_similarity", mock_calculate_max_similarity)

    # 1. Pengecekan _match_cert_for_scoring semantic fallback
    # Kasus 1a: Sim = 0.79 -> harus dianggap tidak cocok (threshold 0.80)
    mock_sim = 0.79
    matched, match_type = _match_cert_for_scoring("Ahli K3", ["Pelatihan K3"])
    assert matched is False
    assert match_type == "none"

    # Kasus 1b: Sim = 0.81 -> harus dianggap cocok (threshold 0.80)
    mock_sim = 0.81
    matched, match_type = _match_cert_for_scoring("Ahli K3", ["Pelatihan K3"])
    assert matched is True
    assert match_type == "semantic"

    # 2. Pengecekan _score_certifications Tier 3 (Bonus)
    requirements = {
        "required_certifications": [],
        "preferred_certifications": [],
        "required_skills": ["Python"],
        "preferred_skills": []
    }
    
    # Kasus 2a: Sim = 0.64 -> tidak terhitung sebagai bonus (threshold 0.65)
    mock_sim = 0.64
    candidate_a = MockCandidate()
    candidate_a.trainings = [MockTraining("Sertifikat Coding")]
    score_a, detail_a = _score_certifications(candidate_a, requirements)
    assert score_a == 0.0
    assert detail_a["bonus_relevant"] == 0

    # Kasus 2b: Sim = 0.66 -> terhitung sebagai bonus (threshold 0.65)
    mock_sim = 0.66
    candidate_b = MockCandidate()
    candidate_b.trainings = [MockTraining("Sertifikat Coding")]
    score_b, detail_b = _score_certifications(candidate_b, requirements)
    assert score_b == 1.0
    assert detail_b["bonus_relevant"] == 1
