"""Utilitas Pencocokan Jurusan Terkonsolidasi (P17).

Menyediakan fungsi terpadu untuk melakukan normalisasi, pembersihan,
dan pencocokan rumpun jurusan secara semantik maupun aturan string.
"""

import logging
import re
from app.config import settings
from core.utils.major_mapping import MAJOR_GROUPS, MAJOR_SYNONYMS

logger = logging.getLogger(__name__)


def normalize_major(major_name: str) -> str:
    """Melakukan normalisasi nama jurusan menggunakan kamus sinonim untuk perbandingan yang konsisten.

    Parameter:
        major_name (str): Nama jurusan yang akan dinormalisasi.

    Return:
        str: Nama jurusan yang telah dinormalisasi (lowercase).
    """
    if not major_name:
        return ""
    cleaned = major_name.strip().lower()
    if cleaned in MAJOR_SYNONYMS:
        return MAJOR_SYNONYMS[cleaned].strip().lower()
    return cleaned


def get_major_group(major: str) -> str | None:
    """Mencari rumpun (group) asal dari nama jurusan.

    Parameter:
        major (str): Nama jurusan.

    Return:
        str | None: Nama rumpun jika ditemukan, None jika tidak.
    """
    major_lower = major.lower()
    for group_name, members in MAJOR_GROUPS.items():
        if group_name.lower() == major_lower:
            return group_name
        for member in members:
            if member.lower() == major_lower:
                return group_name
    return None


def clean_major_for_semantic(major_name: str) -> str:
    """Membersihkan kata sandang akademik dan struktural dari nama jurusan untuk pencocokan semantik.

    Menghapus kata-kata struktural (seperti "program studi", "jurusan") dan kata sandang bias
    rumpun besar (seperti "teknik", "ilmu", "sains") agar tidak mendominasi vektor kemiripan semantik.

    Parameter:
        major_name (str): Nama jurusan yang sudah dinormalisasi.

    Return:
        str: Nama jurusan yang sudah bersih dari stopwords rumpun besar.
    """
    if not major_name:
        return ""

    stopwords_prodi = [
        "program studi", "jurusan", "departemen", "prodi",
        "konsentrasi", "bidang studi", "bidang minat", "bidang", "minat",
        "sarjana", "diploma", "strata 1", "strata 2", "strata 3",
        "s1", "s2", "s3", "d1", "d2", "d3", "d4"
    ]

    cleaned = major_name.lower().strip()
    for sw in stopwords_prodi:
        cleaned = re.sub(rf"\b{re.escape(sw)}\b", "", cleaned)

    bias_words = ["teknik", "ilmu", "sains", "science", "engineering"]
    for bw in bias_words:
        cleaned = re.sub(rf"\b{re.escape(bw)}\b", "", cleaned)

    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if not cleaned:
        return major_name.lower().strip()

    return cleaned


def check_major_match(major: str, allowed_majors: list[str]) -> bool:
    """Memeriksa kesesuaian jurusan kandidat dengan daftar jurusan yang disyaratkan/diperbolehkan.

    Pencocokan menggunakan tiga lapis evaluasi:
    1. Pencocokan string eksak & substring pada nama jurusan yang telah dinormalisasi.
    2. Pencocokan rumpun jurusan (major group flexible matching).
    3. Pencocokan kemiripan semantik (Multilingual-E5) menggunakan threshold yang dikonfigurasi.

    Parameter:
        major (str): Nama jurusan kandidat.
        allowed_majors (list[str]): Daftar nama jurusan yang diperbolehkan.

    Return:
        bool: True jika jurusan kandidat cocok/sejenis, False jika tidak.
    """
    if not allowed_majors:
        return True
    if not major:
        return False

    major_normalized = normalize_major(major)
    if not major_normalized:
        return False

    # Lapis 1: Exact & Substring Matching
    for allowed in allowed_majors:
        allowed_normalized = normalize_major(allowed)
        if not allowed_normalized:
            continue
        if (
            allowed_normalized == major_normalized
            or allowed_normalized in major_normalized
            or major_normalized in allowed_normalized
        ):
            return True

    # Lapis 2: Major Group Matching
    cand_group = get_major_group(major_normalized)
    if cand_group:
        for allowed in allowed_majors:
            allowed_normalized = normalize_major(allowed)
            allowed_group = get_major_group(allowed_normalized)
            if allowed_group and allowed_group == cand_group:
                return True

    # Lapis 3: Semantic Fallback
    from core.filtering.semantic_matcher import semantic_matcher
    
    cleaned_cand_major = clean_major_for_semantic(major_normalized)
    cleaned_allowed_majors = [
        clean_major_for_semantic(normalize_major(allowed))
        for allowed in allowed_majors
    ]
    sim_score, _ = semantic_matcher.calculate_max_similarity(
        cleaned_cand_major, cleaned_allowed_majors
    )
    return sim_score >= settings.SIMILARITY_THRESHOLD_MAJOR
