"""Unit test untuk verifikasi evaluasi taksonomi dan penyelarasan upgrade otomatis (Professional)."""

import sys
sys.path.append('d:/cv-filtering-v1')

from core.filtering.taxonomy_matcher import match_job_role

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


class MockTags:
    def __init__(self, tags):
        self.tags = tags


class MockExperience:
    def __init__(self, role_name, tags, jobdesk="", startyear=2020, endyear=2023):
        self.startdate = None
        self.enddate = None
        self.startyear = startyear
        self.endyear = endyear
        self.iscurrent = False
        self.jobdesk = jobdesk
        self.experience_tags = MockTags(tags)


class MockEducation:
    def __init__(self, major, education_id=3):
        self.education_id = education_id
        self.major = major
        self.score = "3.5"
        self.institutionname = "UI"
        self.startyear = 2016
        self.endyear = 2020


# ═══════════════════════════════════════════════════════════════
# TEST 1: Entry-Level (Trainee/Fresh Graduate) Skill-Based Upgrade
# ═══════════════════════════════════════════════════════════════
print("=" * 60)
print("TEST 1: Entry-Level Skill-Based Upgrade")
print("=" * 60)

# Lowongan: Backend Developer (min_experience_years = 1.0)
# Kandidat: Lulusan baru, pengalaman magang di "IT, Admin" (unrelated/loosely),
# tetapi jobdesk-nya berisi skill "Python" / "FastAPI" yang cocok dengan job_tags.
job_tags = ["IT & Software", "Python", "FastAPI"]
candidate_exps_1 = [
    MockExperience(
        role_name="Admin",
        tags="Administration, Admin Staff",
        jobdesk="Input data using Python and FastAPI framework.",
        startyear=2022,
        endyear=2023 # 12 bulan (1 tahun)
    )
]

result_1 = match_job_role(
    candidate_experiences=candidate_exps_1,
    job_title="Backend Developer",
    min_experience_years=1.0,
    cv_tags_str="IT & Software, Python, FastAPI",
    job_tags=job_tags,
    candidate_educations=[MockEducation("Teknik Informatika")],
    max_experience_years=None,
    is_fresh_graduate=False,
    relaxed=False
)

print("RESULT 1:", result_1)
assert_eq("Entry-level upgraded to related/skills_match", result_1["decision"], "PASS")
assert_eq("Entry-level match_type is related", result_1["match_type"], "related")


# ═══════════════════════════════════════════════════════════════
# TEST 2: Professional Skill-Based Upgrade (Bug Asimetri)
# ═══════════════════════════════════════════════════════════════
print()
print("=" * 60)
print("TEST 2: Professional Skill-Based Upgrade")
print("=" * 60)

# Lowongan: Backend Developer (min_experience_years = 2.0)
# Kandidat: Pengalaman 3 tahun di posisi "IT, Admin" (unrelated/loosely),
# tetapi jobdesk-nya berisi skill "Python" / "FastAPI" yang cocok dengan job_tags.
# Berdasarkan aturan upgrade otomatis, ini harusnya di-upgrade ke "related" 
# sehingga decision-nya menjadi PASS karena relevant_years (3.0 thn) >= min_experience_years (2.0 thn).
candidate_exps_2 = [
    MockExperience(
        role_name="Admin IT",
        tags="Administration, Admin IT",
        jobdesk="Maintain database using Python, FastAPI and PostgreSQL.",
        startyear=2020,
        endyear=2023 # 36 bulan (3 tahun)
    )
]

result_2 = match_job_role(
    candidate_experiences=candidate_exps_2,
    job_title="Backend Developer",
    min_experience_years=2.0,
    cv_tags_str="IT & Software, Python, FastAPI",
    job_tags=job_tags,
    candidate_educations=[MockEducation("Teknik Informatika")],
    max_experience_years=None,
    is_fresh_graduate=False,
    relaxed=False
)

print("RESULT 2:", result_2)
# Di strict mode (relaxed=False), relevant_years (1.5) < min_experience_years (2.0) menghasilkan keputusan FAIL
assert_eq("Professional decision in strict mode is FAIL", result_2["decision"], "FAIL")
assert_eq("Professional upgraded to related", result_2["match_type"], "related")

# Di relaxed mode (Tier 2), kandidat diloloskan ke REVIEW (UNKNOWN) karena total_years (3.0) >= min_experience_years (2.0)
assert_eq("Professional decision in relaxed mode is UNKNOWN (REVIEW)", result_2["relaxed_result"]["decision"], "UNKNOWN")


# ═══════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════
print()
print("=" * 60)
total = passed + failed
print(f"HASIL: {passed}/{total} test PASSED, {failed}/{total} test FAILED")
if failed == 0:
    print("SEMUA TEST TAXONOMY MATCHER BERHASIL!")
else:
    print(f"ADA {failed} TEST GAGAL — asimetri terdeteksi.")
print("=" * 60)
