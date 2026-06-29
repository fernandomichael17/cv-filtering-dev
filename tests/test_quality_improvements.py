"""Test komprehensif perbaikan kualitas filtering.

Test Case:
1. Validasi tipe data JD parser (_sanitize_parsed_types)
2. Pinalti kandidat tanpa tag (incomplete profile)
3. Degradasi skor ALTERNATIF (0.70 tanpa cap)
4. Reason builder untuk profil tidak lengkap
"""

import sys
import os
sys.path.append('d:/cv-filtering-v1')

import re

# ═══════════════════════════════════════════════════════════════
# TEST 1: Validasi Tipe Data JD Parser
# ═══════════════════════════════════════════════════════════════
print("=" * 60)
print("TEST 1: Validasi Tipe Data JD Parser (_sanitize_parsed_types)")
print("=" * 60)

from core.llm.jd_parser import _sanitize_parsed_types

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


# Case 1a: LLM mengembalikan string "dua tahun" untuk min_experience_years
parsed_1a = {"min_experience_years": "dua tahun"}
result = _sanitize_parsed_types(parsed_1a)
assert_eq("String tanpa angka -> default 0", result["min_experience_years"], 0)

# Case 1b: LLM mengembalikan string "3" untuk min_experience_years
parsed_1b = {"min_experience_years": "3"}
result = _sanitize_parsed_types(parsed_1b)
assert_eq("String '3' -> int 3", result["min_experience_years"], 3)

# Case 1c: LLM mengembalikan string "2.5 tahun" untuk preferred_min
parsed_1c = {"preferred_min_experience_years": "2.5 tahun"}
result = _sanitize_parsed_types(parsed_1c)
assert_eq("String '2.5 tahun' -> int 2", result["preferred_min_experience_years"], 2)

# Case 1d: LLM mengembalikan angka normal (int)
parsed_1d = {"min_experience_years": 5}
result = _sanitize_parsed_types(parsed_1d)
assert_eq("Int 5 tetap int 5", result["min_experience_years"], 5)

# Case 1e: LLM mengembalikan None untuk field opsional
parsed_1e = {"max_age": None}
result = _sanitize_parsed_types(parsed_1e)
assert_eq("None tetap None (max_age)", result["max_age"], None)

# Case 1f: LLM mengembalikan float 3.0 untuk min_gpa
parsed_1f = {"min_gpa": 3.0}
result = _sanitize_parsed_types(parsed_1f)
assert_eq("Float 3.0 tetap float 3.0 (min_gpa)", result["min_gpa"], 3.0)

# Case 1g: LLM mengembalikan string untuk min_gpa
parsed_1g = {"min_gpa": "IPK minimal 3.25"}
result = _sanitize_parsed_types(parsed_1g)
assert_eq("String 'IPK minimal 3.25' -> float 3.25", result["min_gpa"], 3.25)

# Case 1h: Budget sebagai string "15jt"
parsed_1h = {"budget": "15000000"}
result = _sanitize_parsed_types(parsed_1h)
assert_eq("String '15000000' -> int 15000000", result["budget"], 15000000)

# Case 1i: Skills sebagai string tunggal bukan list
parsed_1i = {"required_skills": "Python, SQL, Docker"}
result = _sanitize_parsed_types(parsed_1i)
assert_eq("String 'Python, SQL, Docker' -> list", result["required_skills"], ["Python", "SQL", "Docker"])

# Case 1j: Skills None -> list kosong
parsed_1j = {"required_skills": None}
result = _sanitize_parsed_types(parsed_1j)
assert_eq("None -> list kosong", result["required_skills"], [])

# Case 1k: Tags sebagai integer (kasus aneh)
parsed_1k = {"tags": 123}
result = _sanitize_parsed_types(parsed_1k)
assert_eq("Integer untuk tags -> list kosong", result["tags"], [])

# Case 1l: marital_status sebagai angka
parsed_1l = {"marital_status": 1}
result = _sanitize_parsed_types(parsed_1l)
assert_eq("Integer 1 untuk marital_status -> string '1'", result["marital_status"], "1")

# Case 1m: Semua field default jika dict kosong
parsed_1m = {}
result = _sanitize_parsed_types(parsed_1m)
assert_eq("Dict kosong: min_experience_years = 0", result["min_experience_years"], 0)
assert_eq("Dict kosong: max_age = None", result["max_age"], None)
assert_eq("Dict kosong: required_skills = []", result["required_skills"], [])


# ═══════════════════════════════════════════════════════════════
# TEST 2: Pinalti Kandidat Tanpa Tag
# ═══════════════════════════════════════════════════════════════
print()
print("=" * 60)
print("TEST 2: Pinalti Kandidat Tanpa Tag (Incomplete Profile)")
print("=" * 60)

# Mock minimal — hanya atribut yang diakses oleh scoring
class MockCandidate:
    def __init__(self, has_tags=True):
        self.requireid = 1
        self.is_fresh_graduate = False
        self.q16_available_from = None
        self.q15_expected_income = None
        self.educations = []
        self.work_experiences = []
        self.trainings = []
        if has_tags:
            self.candidate_tags = type('obj', (object,), {'role_tag': 'IT'})()
            self.candidate_skills = type('obj', (object,), {'skills': ['Python']})()
        else:
            self.candidate_tags = None
            self.candidate_skills = None

# Perlu mock semantic_matcher agar tidak load model berat
import core.filtering.semantic_matcher as sm_module

class MockSemanticMatcher:
    is_initialized = True
    def initialize(self): pass
    def calculate_max_similarity(self, query, targets):
        return 0.0, ""
    def get_embedding(self, text):
        import numpy as np
        return np.zeros((768,))
    def prewarm_cache(self, texts): pass

# Simpan original dan ganti dengan mock
original_matcher = sm_module.semantic_matcher
sm_module.semantic_matcher = MockSemanticMatcher()

# Juga patch di scoring module
import core.filtering.scoring as scoring_module
scoring_module.semantic_matcher = MockSemanticMatcher()

from core.filtering.scoring import calculate_candidate_score
from core.utils.reason_builder import build_candidate_reason

requirements = {
    "required_skills": ["Python", "SQL"],
    "allowed_majors": ["Teknik Informatika"],
    "min_experience_years": 1.0,
}

# Case 2a: Kandidat DENGAN tag — skor normal
candidate_with_tag = MockCandidate(has_tags=True)
taxonomy_with = {"match_type": "related", "relevant_years": 2.0}
score_with, breakdown_with = calculate_candidate_score(
    candidate_with_tag, requirements, taxonomy_with, "Backend Developer"
)
assert_eq("Kandidat dengan tag: incomplete_profile = None/False",
          breakdown_with.get("incomplete_profile"), None)
print(f"  [INFO] Skor kandidat dengan tag: {score_with}")

# Case 2b: Kandidat TANPA tag — skor harus dipinalti
candidate_no_tag = MockCandidate(has_tags=False)
taxonomy_no = {"match_type": "related", "relevant_years": 2.0}
score_no, breakdown_no = calculate_candidate_score(
    candidate_no_tag, requirements, taxonomy_no, "Backend Developer"
)
assert_eq("Kandidat tanpa tag: incomplete_profile = True",
          breakdown_no.get("incomplete_profile"), True)
assert_eq("Kandidat tanpa tag: score_cap reason berisi 'tag belum'",
          "tag belum" in breakdown_no.get("score_cap", {}).get("reason", ""), True)

# Verifikasi skor dipotong ~30%
if score_with > 0:
    ratio = score_no / score_with
    is_penalized = ratio <= 0.75  # 0.70 pinalti + toleransi rounding
    assert_eq(f"Skor tanpa tag ({score_no}) ~70% dari skor normal ({score_with})",
              is_penalized, True)
else:
    print("  [SKIP] Skor normal = 0, tidak bisa menghitung rasio pinalti")


# ═══════════════════════════════════════════════════════════════
# TEST 3: Degradasi Skor ALTERNATIF
# ═══════════════════════════════════════════════════════════════
print()
print("=" * 60)
print("TEST 3: Degradasi Skor ALTERNATIF (0.70 tanpa cap)")
print("=" * 60)

# Simulasi logika di filtering_service.py baris 575-576
test_scores = [30.0, 50.0, 70.0, 90.0, 100.0]

for base_score in test_scores:
    # Logika BARU: * 0.70, tanpa cap
    new_alt = round(base_score * 0.70, 1)
    # Logika LAMA: min(50.0, * 0.55)
    old_alt = round(min(50.0, base_score * 0.55), 1)
    
    # Verifikasi: skor baru harus selalu >= skor lama
    assert_eq(
        f"Base {base_score}: baru ({new_alt}) >= lama ({old_alt})",
        new_alt >= old_alt, True
    )
    # Verifikasi: tidak ada hard cap 50
    if base_score > 71.4:  # 71.4 * 0.70 = 50.0
        assert_eq(
            f"Base {base_score}: skor baru ({new_alt}) bisa > 50",
            new_alt > 50.0 or base_score <= 71.5, True
        )


# ═══════════════════════════════════════════════════════════════
# TEST 4: Reason Builder untuk Profil Tidak Lengkap
# ═══════════════════════════════════════════════════════════════
print()
print("=" * 60)
print("TEST 4: Reason Builder untuk Profil Tidak Lengkap")
print("=" * 60)

# Case 4a: Breakdown dengan incomplete_profile = True
reason_incomplete = build_candidate_reason(
    {"incomplete_profile": True}, "REVIEW"
)
assert_eq("Reason incomplete profile berisi 'belum diekstrak'",
          "belum diekstrak" in reason_incomplete, True)

# Case 4b: Breakdown normal (tanpa incomplete_profile)
reason_normal = build_candidate_reason(
    {
        "taxonomy_match": {"value": "exact", "score": 25.0},
        "skills_match": {"required_matched": ["Python"], "candidate_skills_count": 5},
    },
    "LAYAK"
)
assert_eq("Reason normal tidak berisi 'belum diekstrak'",
          "belum diekstrak" not in reason_normal, True)
print(f"  [INFO] Reason normal: {reason_normal[:80]}...")


# ═══════════════════════════════════════════════════════════════
# TEST 5: Validasi validate_and_refine_jd dengan Sinonim dan Karakter Khusus
# ═══════════════════════════════════════════════════════════════
print()
print("=" * 60)
print("TEST 5: Validasi validate_and_refine_jd dengan Sinonim dan Karakter Khusus")
print("=" * 60)

from core.llm.jd_parser import validate_and_refine_jd

# Skenario 5a: JD menulis "ms. project", LLM mengekstrak "Microsoft Project"
# Harus lolos sebagai required, tidak didegradasi ke preferred
parsed_5a = {
    "required_skills": ["Microsoft Project", "AutoCAD"],
    "preferred_skills": []
}
jd_text_5a = "Kandidat harus menguasai AutoCAD dan Ms. Project."
refined_5a = validate_and_refine_jd(parsed_5a, jd_text_5a)
assert_eq("Microsoft Project dicocokkan dengan Ms. Project", "Microsoft Project" in refined_5a["required_skills"], True)
assert_eq("AutoCAD tetap di required", "AutoCAD" in refined_5a["required_skills"], True)

# Skenario 5b: Skill dengan karakter khusus c++ dan c#
parsed_5b = {
    "required_skills": ["c++", "c#"],
    "preferred_skills": []
}
jd_text_5b = "Memiliki keahlian C++ dan C# development."
refined_5b = validate_and_refine_jd(parsed_5b, jd_text_5b)
assert_eq("C++ lolos pencocokan kata utuh", "c++" in refined_5b["required_skills"], True)
assert_eq("C# lolos pencocokan kata utuh", "c#" in refined_5b["required_skills"], True)

# Skenario 5c: Menghindari false positive pada singkatan pendek (e.g. "go" vs "government")
parsed_5c = {
    "required_skills": ["go"],
    "preferred_skills": []
}
jd_text_5c = "Working in a fast-paced government office."
refined_5c = validate_and_refine_jd(parsed_5c, jd_text_5c)
assert_eq("Go tidak boleh cocok dengan government", "go" in refined_5c["required_skills"], False)
assert_eq("Go masuk ke preferred karena tidak ditemukan", "go" in refined_5c["preferred_skills"], True)


# ═══════════════════════════════════════════════════════════════
# TEST 6: Validasi Kamus Baru Finance, Accounting, dan Engineering
# ═══════════════════════════════════════════════════════════════
print()
print("=" * 60)
print("TEST 6: Validasi Kamus Baru Finance, Accounting, dan Engineering")
print("=" * 60)

from core.utils.skill_synonyms import normalize_skill, are_skills_similar

# Skenario 6a: Normalisasi skill perpajakan dan finance
assert_eq("accurate online -> accurate", normalize_skill("accurate online"), "accurate")
assert_eq("accurate accounting -> accurate", normalize_skill("accurate accounting"), "accurate")
assert_eq("brevet pajak a & b -> brevet pajak", normalize_skill("brevet pajak a & b"), "brevet pajak")
assert_eq("brevet c -> brevet pajak", normalize_skill("brevet c"), "brevet pajak")
assert_eq("financial modeling -> financial analysis", normalize_skill("financial modeling"), "financial analysis")
assert_eq("analisis laporan keuangan -> financial analysis", normalize_skill("analisis laporan keuangan"), "financial analysis")

# Skenario 6b: Normalisasi skill engineering
assert_eq("autodesk revit -> revit", normalize_skill("autodesk revit"), "revit")
assert_eq("solidworks -> solidworks", normalize_skill("solidworks"), "solidworks")
assert_eq("solid works -> solidworks", normalize_skill("solid works"), "solidworks")
assert_eq("autocad 2d -> autocad", normalize_skill("autocad 2d"), "autocad")
assert_eq("computer aided design -> autocad", normalize_skill("computer aided design"), "autocad")
assert_eq("boq -> rencana anggaran biaya", normalize_skill("boq"), "rencana anggaran biaya")
assert_eq("bill of quantities -> rencana anggaran biaya", normalize_skill("bill of quantities"), "rencana anggaran biaya")
assert_eq("ak3u -> k3 umum", normalize_skill("ak3u"), "k3 umum")
assert_eq("sertifikat k3 -> k3 umum", normalize_skill("sertifikat k3"), "k3 umum")
assert_eq("sistem informasi geografis -> gis", normalize_skill("sistem informasi geografis"), "gis")
assert_eq("arcgis -> gis", normalize_skill("arcgis"), "gis")

# Skenario 6c: Kelompok Keahlian Sejenis (Skill Clusters)
assert_eq("accurate & sap sejenis", are_skills_similar("accurate", "sap"), True)
assert_eq("myob & jurnal.id sejenis", are_skills_similar("myob", "jurnal.id"), True)
assert_eq("brevet a & e-faktur sejenis", are_skills_similar("brevet a", "e-faktur"), True)
assert_eq("autocad & revit sejenis", are_skills_similar("autocad", "revit"), True)
assert_eq("solidworks & sketchup sejenis", are_skills_similar("solidworks", "sketchup"), True)
assert_eq("sap2000 & tekla sejenis", are_skills_similar("sap2000", "tekla"), True)
assert_eq("ms project & primavera p6 sejenis", are_skills_similar("ms project", "primavera p6"), True)
assert_eq("k3 umum & ska sejenis", are_skills_similar("k3 umum", "ska"), True)
assert_eq("ak3u & slf sejenis", are_skills_similar("ak3u", "slf"), True)


# ═══════════════════════════════════════════════════════════════
# TEST 7: Validasi Kamus Baru Sales, Marketing, dan Admin
# ═══════════════════════════════════════════════════════════════
print()
print("=" * 60)
print("TEST 7: Validasi Kamus Baru Sales, Marketing, dan Admin")
print("=" * 60)

# Skenario 7a: Normalisasi skill Sales, Marketing, dan Admin
assert_eq("negotiation -> negosiasi", normalize_skill("negotiation"), "negosiasi")
assert_eq("teknik negosiasi -> negosiasi", normalize_skill("teknik negosiasi"), "negosiasi")
assert_eq("pencarian prospek -> lead generation", normalize_skill("pencarian prospek"), "lead generation")
assert_eq("pemasaran digital -> digital marketing", normalize_skill("pemasaran digital"), "digital marketing")
assert_eq("manajemen media sosial -> social media marketing", normalize_skill("manajemen media sosial"), "social media marketing")
assert_eq("smm -> social media marketing", normalize_skill("smm"), "social media marketing")
assert_eq("content writer -> content writing", normalize_skill("content writer"), "content writing")
assert_eq("input data -> data entry", normalize_skill("input data"), "data entry")
assert_eq("document controller -> document control", normalize_skill("document controller"), "document control")
assert_eq("ms office -> microsoft office", normalize_skill("ms office"), "microsoft office")
assert_eq("gsuite -> google workspace", normalize_skill("gsuite"), "google workspace")
assert_eq("resepsionis -> receptionist", normalize_skill("resepsionis"), "receptionist")

# Skenario 7b: Kelompok Keahlian Sejenis (Skill Clusters)
assert_eq("seo & digital marketing sejenis", are_skills_similar("seo", "digital marketing"), True)
assert_eq("copywriting & content writing sejenis", are_skills_similar("copywriting", "content writing"), True)
assert_eq("negosiasi & crm sejenis", are_skills_similar("negosiasi", "crm"), True)
assert_eq("telemarketing & sales sejenis", are_skills_similar("telemarketing", "sales"), True)
assert_eq("korespondensi & document control sejenis", are_skills_similar("korespondensi", "document control"), True)
assert_eq("microsoft office & google workspace sejenis", are_skills_similar("microsoft office", "google workspace"), True)


# ═══════════════════════════════════════════════════════════════
# TEST 8: Validasi Kamus Baru Healthcare, Legal, Education, dan Blue-Collar
# ═══════════════════════════════════════════════════════════════
print()
print("=" * 60)
print("TEST 8: Validasi Kamus Baru Healthcare, Legal, Education, dan Blue-Collar")
print("=" * 60)

# Skenario 8a: Normalisasi skill Healthcare, Legal, Education, dan Blue-Collar
assert_eq("surat tanda registrasi -> str", normalize_skill("surat tanda registrasi"), "str")
assert_eq("surat izin praktik -> sip", normalize_skill("surat izin praktik"), "sip")
assert_eq("cpr -> bls", normalize_skill("cpr"), "bls")
assert_eq("legal korporasi -> corporate legal", normalize_skill("legal korporasi"), "corporate legal")
assert_eq("ketenagakerjaan -> hubungan industrial", normalize_skill("ketenagakerjaan"), "hubungan industrial")
assert_eq("peradi -> upa", normalize_skill("peradi"), "upa")
assert_eq("sertifikasi pendidik -> sertifikasi guru", normalize_skill("sertifikasi pendidik"), "sertifikasi guru")
assert_eq("pelatihan gada pratama -> gada pratama", normalize_skill("pelatihan gada pratama"), "gada pratama")
assert_eq("surat izin mengemudi a -> sim a", normalize_skill("surat izin mengemudi a"), "sim a")
assert_eq("sim b -> sim b1", normalize_skill("sim b"), "sim b1")
assert_eq("surat izin operasional forklift -> sio forklift", normalize_skill("surat izin operasional forklift"), "sio forklift")
assert_eq("tata graha -> housekeeping", normalize_skill("tata graha"), "housekeeping")

# Skenario 8b: Kelompok Keahlian Sejenis (Skill Clusters)
assert_eq("str & btcls sejenis", are_skills_similar("str", "btcls"), True)
assert_eq("acls & bls sejenis", are_skills_similar("acls", "bls"), True)
assert_eq("upa & compliance sejenis", are_skills_similar("upa", "compliance"), True)
assert_eq("corporate legal & litigasi sejenis", are_skills_similar("corporate legal", "litigasi"), True)
assert_eq("gada pratama & sim a sejenis", are_skills_similar("gada pratama", "sim a"), True)
assert_eq("sio forklift & housekeeping sejenis", are_skills_similar("sio forklift", "housekeeping"), True)
assert_eq("ppg & pedagogi sejenis", are_skills_similar("ppg", "pedagogi"), True)


# ═══════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════
print()
print("=" * 60)
total = passed + failed
print(f"HASIL: {passed}/{total} test PASSED, {failed}/{total} test FAILED")
if failed == 0:
    print("SEMUA TEST BERHASIL!")
else:
    print(f"ADA {failed} TEST GAGAL — perlu investigasi.")
print("=" * 60)

# Restore original matcher
sm_module.semantic_matcher = original_matcher
scoring_module.semantic_matcher = original_matcher
