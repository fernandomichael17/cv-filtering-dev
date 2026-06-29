"""Reason Builder — Template-based reason trail untuk keputusan filtering.

Menghasilkan alasan keputusan yang transparan dan detail
berdasarkan data breakdown scoring. Digunakan sebagai pengganti
reason LLM evaluator saat toggle ENABLE_LLM_EVALUATOR dimatikan.
"""


def build_candidate_reason(breakdown: dict, decision: str) -> str:
    """Membangun alasan keputusan filtering dari data breakdown scoring.

    Format output disesuaikan berdasarkan decision tier:
    - LAYAK: menekankan kecocokan yang ditemukan
    - REVIEW: menekankan area yang perlu verifikasi manual
    - ALTERNATIF: menekankan bahwa kandidat dari bidang berdekatan

    Parameter:
        breakdown (dict): Rincian skor per komponen dari calculate_candidate_score().
        decision (str): Keputusan akhir (LAYAK, REVIEW, ALTERNATIF).

    Return:
        str: Alasan keputusan dalam format teks terstruktur.
    """
    if breakdown.get("incomplete_profile"):
        return "Data profil kurang lengkap (kandidat belum diekstrak tagnya oleh sistem)."

    parts = []

    # 1. Kecocokan bidang (taxonomy)
    tax_info = breakdown.get("taxonomy_match", {})
    tax_type = tax_info.get("value", "unknown")
    tax_label = _taxonomy_label(tax_type)
    parts.append(f"Kecocokan bidang: {tax_label}")

    # 2. Kecocokan skill wajib
    skills_info = breakdown.get("skills_match", {})
    req_matched = skills_info.get("required_matched", [])
    total_skills = skills_info.get("candidate_skills_count", 0)
    note = skills_info.get("note", "")

    if note == "No skills requirement in JD":
        parts.append("Tidak ada persyaratan skill wajib di lowongan")
    elif note == "Smart Fallback used":
        if req_matched:
            matched_names = [_clean_skill_name(s) for s in req_matched]
            parts.append(f"Skill relevan (fallback): {', '.join(matched_names)}")
    else:
        # Hitung total required dari JD (bukan dari matched)
        hard_matched = [s for s in req_matched if "(semantic)" not in s]
        semantic_matched = [s for s in req_matched if "(semantic)" in s]

        if req_matched:
            matched_names = [_clean_skill_name(s) for s in req_matched]
            parts.append(f"Skill wajib terpenuhi: {', '.join(matched_names)}")
        else:
            parts.append("Skill wajib terpenuhi: tidak ada")

    # 3. Kecocokan skill tambahan (preferred)
    pref_matched = skills_info.get("preferred_matched", [])
    if pref_matched:
        pref_names = [_clean_skill_name(s) for s in pref_matched]
        parts.append(f"Skill tambahan: {', '.join(pref_names)}")

    # 4. Catatan khusus per decision
    if decision == "REVIEW":
        if tax_type in ("loosely_related", "skills_match", "unknown"):
            parts.append("Perlu verifikasi manual — kecocokan bidang tidak pasti")
    elif decision == "ALTERNATIF":
        parts.append("Kandidat dari bidang berdekatan, pertimbangkan jika pool utama kurang")

    return ". ".join(parts) + "."


def _taxonomy_label(match_type: str) -> str:
    """Menerjemahkan kode match_type taxonomy ke label yang dapat dibaca HR.

    Parameter:
        match_type (str): Kode match_type dari taxonomy matcher.

    Return:
        str: Label deskriptif dalam Bahasa Indonesia.
    """
    labels = {
        "exact": "sangat sesuai (exact match)",
        "related": "serumpun (related)",
        "loosely_related": "Relevansi Sebagian (Partially Relevant)",
        "skills_match": "kecocokan berbasis skill",
        "unknown": "tidak dapat ditentukan secara otomatis",
        "no_experience": "tanpa pengalaman kerja relevan",
        "unrelated": "tidak terkait",
        "field_mismatch": "bidang tidak kompatibel",
    }
    return labels.get(match_type, match_type)


def _clean_skill_name(skill: str) -> str:
    """Membersihkan nama skill dari suffix match type.

    Parameter:
        skill (str): Nama skill dengan kemungkinan suffix seperti '(semantic)' atau '(0.85)'.

    Return:
        str: Nama skill yang bersih.
    """
    # Hapus suffix (semantic), (hard), atau (0.XX)
    cleaned = skill.strip()
    if cleaned.endswith(")"):
        paren_start = cleaned.rfind("(")
        if paren_start > 0:
            suffix = cleaned[paren_start + 1:-1].strip()
            if suffix in ("semantic", "hard") or _is_float(suffix):
                cleaned = cleaned[:paren_start].strip()
    return cleaned


def _is_float(s: str) -> bool:
    """Memeriksa apakah string merupakan bilangan desimal.

    Parameter:
        s (str): String yang akan diperiksa.

    Return:
        bool: True jika string bisa dikonversi ke float.
    """
    try:
        float(s)
        return True
    except ValueError:
        return False
