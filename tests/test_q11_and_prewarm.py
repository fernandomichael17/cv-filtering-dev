"""Test untuk verifikasi pre-warming cache semantik (Optimasi Latensi)."""

import sys
sys.path.append('d:/cv-filtering-v1')

from app.services.filtering_service import _prewarm_caches

passed = 0
failed = 0

def assert_eq(test_name, actual, expected):
    global passed, failed
    if actual == expected:
        print(f"  [PASS] {test_name}")
        passed += 1
    else:
        print(f"  [FAIL] {test_name}: expected {expected!r}, got {actual!r}")
        failed += 1


# Mock objek kandidat Require ORM
class MockCandidate:
    def __init__(self, name, educations=None, work_experiences=None, trainings=None):
        self.requireid = 101
        self.firstname = name.split()[0]
        self.lastname = name.split()[1] if len(name.split()) > 1 else ""
        self.gender = None
        self.dateofbirth = "1995-01-01"
        self.marital_status = None
        self.is_fresh_graduate = False
        self.educations = educations or []
        self.work_experiences = work_experiences or []
        self.trainings = trainings or []


# ═══════════════════════════════════════════════════════════════
# TEST 1: Pre-warm Cache Semantik
# ═══════════════════════════════════════════════════════════════
print("=" * 60)
print("TEST: Pre-warm Cache Semantik")
print("=" * 60)

# Mock semantic matcher to prevent actual network calls during test
import core.filtering.semantic_matcher as sm_module
class MockSemanticMatcher:
    is_initialized = True
    def __init__(self):
        self.prewarmed = []
    def initialize(self): pass
    def prewarm_cache(self, texts):
        self.prewarmed.extend(texts)

original_matcher = sm_module.semantic_matcher
mock_matcher = MockSemanticMatcher()
sm_module.semantic_matcher = mock_matcher

# Data untuk prewarm
test_cand = MockCandidate("Budi Santoso")
test_cand.educations = [
    type('obj', (object,), {'education_id': 3, 'major': 'Teknik Informatika', 'institutionname': 'UI'})()
]
test_cand.trainings = [
    type('obj', (object,), {'trainingname': 'AWS Certified Cloud Practitioner'})()
]
test_cand.candidate_skills = type('obj', (object,), {'hard_skill': 'Python, SQL', 'soft_skill': 'Communication', 'language': 'English'})()

reqs = {
    "allowed_majors": ["Teknik Informatika", "Ilmu Komputer"],
    "required_skills": ["Python"],
    "preferred_skills": ["SQL"],
    "required_certifications": ["AWS Practitioner"],
    "preferred_certifications": []
}

_prewarm_caches([test_cand], reqs, ["IT", "Developer"], "Backend Developer")

# Verifikasi yang di-prewarm
prewarmed_set = set(mock_matcher.prewarmed)
assert_eq("Prewarm berisi tag", "passage: it" in prewarmed_set, True)
assert_eq("Prewarm berisi major", "passage: teknik informatika" in prewarmed_set, True)
assert_eq("Prewarm berisi skill JD", "query: python" in prewarmed_set, True)
assert_eq("Prewarm berisi skill kandidat", "passage: python" in prewarmed_set, True)
assert_eq("Prewarm berisi sertifikasi JD", "query: aws practitioner" in prewarmed_set, True)
assert_eq("Prewarm berisi sertifikasi kandidat", "passage: aws certified cloud practitioner" in prewarmed_set, True)

# Restore
sm_module.semantic_matcher = original_matcher


# ═══════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════
print()
print("=" * 60)
total = passed + failed
print(f"HASIL: {passed}/{total} test PASSED, {failed}/{total} test FAILED")
if failed == 0:
    print("SEMUA TEST PREWARM BERHASIL!")
else:
    print(f"ADA {failed} TEST GAGAL.")
print("=" * 60)
