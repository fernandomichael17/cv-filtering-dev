"""Confidence Calculator — Menghitung tingkat keyakinan sistem terhadap hasil matching.

Menggunakan kombinasi kualitas taxonomy match, skills match, dan kelengkapan data
untuk menghasilkan label confidence ("high", "medium", "low") per kandidat.
"""

import logging

logger = logging.getLogger(__name__)


def calculate_confidence(breakdown: dict, decision: str) -> str:
    """Menghitung tingkat keyakinan (confidence) sistem terhadap hasil filtering kandidat.

    Faktor yang dipertimbangkan:
    1. Taxonomy match type (exact/related/loosely/unknown)
    2. Persentase kecocokan skill wajib (hard match vs semantic)
    3. Status profil lengkap/tidak
    4. Keputusan akhir (LAYAK/REVIEW/ALTERNATIF)

    Parameter:
        breakdown (dict): Rincian skor per komponen dari calculate_candidate_score().
        decision (str): Keputusan akhir filtering (LAYAK, REVIEW, ALTERNATIF).

    Return:
        str: Tingkat keyakinan ("high", "medium", "low").
    """
    # Jika profil tidak lengkap, langsung low
    if breakdown.get("incomplete_profile"):
        return "low"

    score = 0  # Skor internal untuk menentukan threshold

    # ── Faktor 1: Taxonomy Match (max 40 poin) ──
    tax_info = breakdown.get("taxonomy_match", {})
    tax_type = tax_info.get("value", "unknown")

    tax_points = {
        "exact": 40,
        "related": 30,
        "skills_match": 15,
        "loosely_related": 10,
        "unknown": 0,
        "no_experience": 5,
        "unrelated": 0,
    }
    score += tax_points.get(tax_type, 0)

    # ── Faktor 2: Skills Match Quality (max 35 poin) ──
    skills_info = breakdown.get("skills_match", {})
    req_matched = skills_info.get("required_matched", [])
    note = skills_info.get("note", "")

    if note == "No skills requirement in JD":
        # Tidak ada data skill di JD — kurang yakin
        score += 10
    elif note == "Smart Fallback used":
        # Fallback, tidak ada skill requirement di JD
        score += 15
    else:
        # Hitung rasio hard match vs semantic match
        hard_matches = [s for s in req_matched if "(semantic)" not in s]
        semantic_matches = [s for s in req_matched if "(semantic)" in s]
        total_matched = len(req_matched)

        if total_matched > 0:
            hard_ratio = len(hard_matches) / max(1, total_matched)
            # Semakin banyak hard match (bukan semantic), semakin yakin
            score += int(hard_ratio * 25)
            # Bonus jika ada match sama sekali
            score += 10
        # Jika tidak ada match sama sekali, 0 poin

    # ── Faktor 3: Keputusan (max 25 poin) ──
    decision_points = {
        "LAYAK": 25,
        "REVIEW": 10,
        "ALTERNATIF": 5,
    }
    score += decision_points.get(decision, 0)

    # ── Tentukan Label ──
    if score >= 70:
        confidence = "high"
    elif score >= 35:
        confidence = "medium"
    else:
        confidence = "low"

    # ── Post-processing Capping ──
    # ALTERNATIF selalu memiliki confidence medium atau low
    if decision == "ALTERNATIF" and confidence == "high":
        confidence = "medium"

    # Jika menggunakan Smart Fallback dan taxonomy match bukan exact, batasi confidence maksimal medium
    if note == "Smart Fallback used" and tax_type != "exact" and confidence == "high":
        confidence = "medium"

    logger.debug(
        "Confidence score=%d -> %s (tax=%s, skills_matched=%d, decision=%s)",
        score, confidence, tax_type, len(req_matched), decision
    )

    return confidence
