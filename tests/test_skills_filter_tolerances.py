"""Unit test untuk verifikasi toleransi skills filter berdasarkan kecocokan taksonomi peran."""

import sys
sys.path.append('d:/cv-filtering-dev-git')

from core.filtering.skills_filter import apply_skills_filter


class MockCandidateTags:
    def __init__(self, tags):
        self.tags = tags


class MockCandidateSkills:
    def __init__(self, hard_skill="", soft_skill="", language=""):
        self.hard_skill = hard_skill
        self.soft_skill = soft_skill
        self.language = language


class MockCandidate:
    def __init__(self, requireid, firstname, lastname, hard_skill="", educations=None):
        self.requireid = requireid
        self.firstname = firstname
        self.lastname = lastname
        self.educations = educations or []
        self.work_experiences = []
        self.trainings = []
        self.candidate_tags = MockCandidateTags("")
        self.candidate_skills = MockCandidateSkills(hard_skill=hard_skill)
        self.is_fresh_graduate = False


class MockEducation:
    def __init__(self, major, education_id=3):
        self.education_id = education_id
        self.major = major
        self.score = "3.5"
        self.institutionname = "UI"


def test_skills_filter_tolerances():
    # Setup requirements
    requirements = {
        "required_skills": ["PHP", "Laravel"],
        "preferred_skills": [],
        "allowed_majors": ["Teknik Informatika", "Sistem Informasi"],
        "major_flexibility": "flexible"
    }

    # 1. Candidate A: Web Developer (exact match) but Golang/NodeJS skills (no match)
    cand_a = MockCandidate(
        requireid=101,
        firstname="Budi",
        lastname="Santoso",
        hard_skill="Golang, NodeJS, SQL",
        educations=[MockEducation("Teknik Informatika")]
    )
    
    # 2. Candidate B: Accountant (unrelated match) and Golang/NodeJS skills (no match)
    cand_b = MockCandidate(
        requireid=102,
        firstname="Siti",
        lastname="Aminah",
        hard_skill="Golang, NodeJS",
        educations=[MockEducation("Akuntansi")]
    )

    # Mock taxonomy results
    taxonomy_results = {
        101: {"match_type": "exact", "reason": "Pengalaman sebagai Web Developer."},
        102: {"match_type": "unrelated", "reason": "Pengalaman sebagai Akuntan tidak relevan."}
    }

    # Jalankan apply_skills_filter
    passed, eliminated = apply_skills_filter(
        candidates=[cand_a, cand_b],
        requirements=requirements,
        min_match_ratio=0.5,
        taxonomy_results=taxonomy_results
    )

    passed_ids = {c.requireid for c in passed}
    eliminated_ids = {e["require_id"] for e in eliminated}

    print("Passed:", passed_ids)
    print("Eliminated:", eliminated_ids)

    # Candidate A (Web Developer) harus lolos karena pengecualian peran exact
    assert 101 in passed_ids, "Candidate A (Web Developer) should pass skills filter due to exact role match"
    assert 101 not in eliminated_ids, "Candidate A should not be eliminated"

    # Candidate B (Accountant) harus tereliminasi karena unrelated role & no skill match
    assert 102 in eliminated_ids, "Candidate B (Accountant) should be eliminated"
    assert 102 not in passed_ids, "Candidate B should not pass skills filter"

    print("TEST SUCCESSFUL!")


if __name__ == "__main__":
    test_skills_filter_tolerances()
