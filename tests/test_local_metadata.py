"""Test untuk verifikasi penyimpanan metadata analitik AI ke SQLite lokal terpisah."""

import sys
sys.path.append('d:/cv-filtering-v1')

import os
from app.repositories.local_metadata_repository import LocalMetadataRepository

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


# Inisialisasi repository metadata
local_repo = LocalMetadataRepository()

# Hapus data sampah test sebelumnya jika ada
JOB_ID = 9999
local_repo.delete_metadata_by_job_id(JOB_ID)


# ═══════════════════════════════════════════════════════════════
# TEST 1: Penyimpanan dan Pengambilan Metadata Bulk
# ═══════════════════════════════════════════════════════════════
print("=" * 60)
print("TEST 1: Penyimpanan dan Pengambilan Metadata Bulk")
print("=" * 60)

test_data = [
    {
        "require_id": 1,
        "confidence": "high",
        "total_score": 85.5,
        "score_breakdown": {"skills_match": 20.0, "experience_surplus": 10.0}
    },
    {
        "require_id": 2,
        "confidence": "medium",
        "total_score": 65.0,
        "score_breakdown": {"skills_match": 15.0}
    }
]

# Simpan
local_repo.save_metadata_bulk(JOB_ID, test_data)

# Ambil
results = local_repo.get_metadata_by_job_id(JOB_ID)

assert_eq("Jumlah data terambil cocok", len(results), 2)
assert_eq("Data kandidat 1 terambil", 1 in results, True)
if 1 in results:
    assert_eq("Confidence kandidat 1 cocok", results[1]["confidence"], "high")
    assert_eq("Score kandidat 1 cocok", results[1]["total_score"], 85.5)
    assert_eq("Breakdown kandidat 1 cocok", results[1]["score_breakdown"].get("skills_match"), 20.0)

assert_eq("Data kandidat 2 terambil", 2 in results, True)
if 2 in results:
    assert_eq("Confidence kandidat 2 cocok", results[2]["confidence"], "medium")
    assert_eq("Score kandidat 2 cocok", results[2]["total_score"], 65.0)


# ═══════════════════════════════════════════════════════════════
# TEST 2: Pembaruan Data (INSERT OR REPLACE)
# ═══════════════════════════════════════════════════════════════
print()
print("=" * 60)
print("TEST 2: Pembaruan Data (INSERT OR REPLACE)")
print("=" * 60)

update_data = [
    {
        "require_id": 2,
        "confidence": "low",
        "total_score": 30.0,
        "score_breakdown": {"skills_match": 5.0}
    }
]

# Simpan pembaruan untuk require_id 2
local_repo.save_metadata_bulk(JOB_ID, update_data)

results_updated = local_repo.get_metadata_by_job_id(JOB_ID)
assert_eq("Jumlah total data setelah update tetap 2", len(results_updated), 2)
if 2 in results_updated:
    assert_eq("Confidence kandidat 2 terupdate", results_updated[2]["confidence"], "low")
    assert_eq("Score kandidat 2 terupdate", results_updated[2]["total_score"], 30.0)


# ═══════════════════════════════════════════════════════════════
# TEST 3: Pembersihan Data (DELETE)
# ═══════════════════════════════════════════════════════════════
print()
print("=" * 60)
print("TEST 3: Pembersihan Data (DELETE)")
print("=" * 60)

local_repo.delete_metadata_by_job_id(JOB_ID)
results_deleted = local_repo.get_metadata_by_job_id(JOB_ID)
assert_eq("Data terhapus sepenuhnya", len(results_deleted), 0)


# ═══════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════
print()
print("=" * 60)
total = passed + failed
print(f"HASIL: {passed}/{total} test PASSED, {failed}/{total} test FAILED")
if failed == 0:
    print("SEMUA TEST LOCAL METADATA SQLITE BERHASIL!")
else:
    print(f"ADA {failed} TEST GAGAL.")
print("=" * 60)
