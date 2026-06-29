"""Test confidence level dan verifikasi logging semantic fallback.

Test Case:
1. Confidence = high (taxonomy exact + skills hard match + LAYAK)
2. Confidence = medium (taxonomy related + beberapa skill semantic)
3. Confidence = low (taxonomy unknown + tidak ada skill match)
4. Confidence = low (incomplete profile)
5. Confidence ALTERNATIF selalu medium atau low
"""

import sys
sys.path.append('d:/cv-filtering-v1')

from core.utils.confidence import calculate_confidence

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


# ═══════════════════════════════════════════════════════════════
# TEST 1: Confidence HIGH
# ═══════════════════════════════════════════════════════════════
print("=" * 60)
print("TEST 1: Confidence HIGH")
print("=" * 60)

breakdown_high = {
    "taxonomy_match": {"value": "exact", "score": 25.0},
    "skills_match": {
        "required_matched": ["Python", "SQL", "Docker"],
        "preferred_matched": ["AWS"],
        "candidate_skills_count": 10,
        "score": 15.0,
    },
}
result = calculate_confidence(breakdown_high, "LAYAK")
assert_eq("Taxonomy exact + 3 hard skills + LAYAK = high", result, "high")


# ═══════════════════════════════════════════════════════════════
# TEST 2: Confidence MEDIUM
# ═══════════════════════════════════════════════════════════════
print()
print("=" * 60)
print("TEST 2: Confidence MEDIUM")
print("=" * 60)

# Case 2a: Taxonomy related + beberapa skill cocok via semantic
breakdown_med_a = {
    "taxonomy_match": {"value": "related", "score": 17.0},
    "skills_match": {
        "required_matched": ["Python (semantic)", "SQL (semantic)"],
        "candidate_skills_count": 5,
        "score": 9.0,
    },
}
result_a = calculate_confidence(breakdown_med_a, "LAYAK")
assert_eq("Taxonomy related + 2 semantic skills + LAYAK = medium", result_a, "medium")

# Case 2b: Taxonomy exact + no skills requirement
breakdown_med_b = {
    "taxonomy_match": {"value": "exact", "score": 25.0},
    "skills_match": {
        "required_matched": [],
        "score": 0.0,
        "note": "No skills requirement in JD",
    },
}
result_b = calculate_confidence(breakdown_med_b, "LAYAK")
assert_eq("Taxonomy exact + no skills in JD + LAYAK = high", result_b, "high")

# Case 2c: REVIEW decision
breakdown_med_c = {
    "taxonomy_match": {"value": "loosely_related", "score": 3.0},
    "skills_match": {
        "required_matched": ["Python", "SQL"],
        "candidate_skills_count": 5,
        "score": 9.0,
    },
}
result_c = calculate_confidence(breakdown_med_c, "REVIEW")
assert_eq("Taxonomy loosely + 2 hard skills + REVIEW = medium", result_c, "medium")


# ═══════════════════════════════════════════════════════════════
# TEST 3: Confidence LOW
# ═══════════════════════════════════════════════════════════════
print()
print("=" * 60)
print("TEST 3: Confidence LOW")
print("=" * 60)

# Case 3a: Taxonomy unknown + no skills
breakdown_low_a = {
    "taxonomy_match": {"value": "unknown", "score": 0.0},
    "skills_match": {
        "required_matched": [],
        "candidate_skills_count": 0,
        "score": 0.0,
    },
}
result_low_a = calculate_confidence(breakdown_low_a, "REVIEW")
assert_eq("Taxonomy unknown + 0 skills + REVIEW = low", result_low_a, "low")

# Case 3b: Incomplete profile
breakdown_low_b = {
    "incomplete_profile": True,
    "taxonomy_match": {"value": "exact", "score": 25.0},
    "skills_match": {"required_matched": ["Python"], "score": 9.0},
}
result_low_b = calculate_confidence(breakdown_low_b, "LAYAK")
assert_eq("Incomplete profile (meskipun taxonomy exact) = low", result_low_b, "low")


# ═══════════════════════════════════════════════════════════════
# TEST 4: Confidence untuk ALTERNATIF
# ═══════════════════════════════════════════════════════════════
print()
print("=" * 60)
print("TEST 4: Confidence untuk ALTERNATIF")
print("=" * 60)

breakdown_alt = {
    "taxonomy_match": {"value": "related", "score": 17.0},
    "skills_match": {
        "required_matched": ["Python"],
        "candidate_skills_count": 3,
        "score": 4.5,
    },
}
result_alt = calculate_confidence(breakdown_alt, "ALTERNATIF")
assert_eq("ALTERNATIF selalu medium atau low", result_alt in ("medium", "low"), True)
print(f"  [INFO] ALTERNATIF confidence: {result_alt}")


# ═══════════════════════════════════════════════════════════════
# TEST 5: Edge Cases
# ═══════════════════════════════════════════════════════════════
print()
print("=" * 60)
print("TEST 5: Edge Cases")
print("=" * 60)

# Case 5a: Semua semantic match (0 hard match)
breakdown_all_semantic = {
    "taxonomy_match": {"value": "exact", "score": 25.0},
    "skills_match": {
        "required_matched": ["Python (semantic)", "SQL (semantic)", "Docker (semantic)"],
        "candidate_skills_count": 5,
        "score": 9.0,
    },
}
result_5a = calculate_confidence(breakdown_all_semantic, "LAYAK")
# Taxonomy exact (40) + all semantic skills (10 bonus, 0 hard ratio * 25 = 0) + LAYAK (25) = 75 -> high
# Wait: hard_ratio = 0/3 = 0, so score += 0 + 10 = 10. Total = 40 + 10 + 25 = 75 -> high
assert_eq("Taxonomy exact + semua semantic skills + LAYAK = high", result_5a, "high")

# Case 5b: Breakdown kosong
breakdown_empty = {}
result_5b = calculate_confidence(breakdown_empty, "REVIEW")
assert_eq("Breakdown kosong + REVIEW = low", result_5b, "low")

# Case 5c: Smart Fallback
breakdown_fallback = {
    "taxonomy_match": {"value": "related", "score": 17.0},
    "skills_match": {
        "required_matched": ["Excel (0.65)"],
        "score": 5.0,
        "note": "Smart Fallback used",
    },
}
result_5c = calculate_confidence(breakdown_fallback, "LAYAK")
assert_eq("Smart Fallback + related + LAYAK = medium", result_5c, "medium")


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
