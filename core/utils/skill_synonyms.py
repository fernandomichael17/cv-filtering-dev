"""Skill synonyms dictionary and normalization utility.

Menyediakan dua mekanisme normalisasi:
1. SYMBOL_NORMALIZATION_MAP — menangani karakter non-alfanumerik (c++ → cpp, .net → dotnet).
2. SKILL_SYNONYMS — memetakan variasi nama ke bentuk kanonik (reactjs → react).

Data dimuat secara dinamis dari core/utils/data/skill_synonyms.json.
"""

import json
import logging
import os

logger = logging.getLogger(__name__)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DATA_PATH = os.path.join(CURRENT_DIR, "data", "skill_synonyms.json")

# Variabel global untuk menyimpan data
SYMBOL_NORMALIZATION_MAP: dict[str, str] = {}
SKILL_SYNONYMS: dict[str, list[str]] = {}
SKILL_CLUSTERS: list[set[str]] = []
SKILL_EXCLUSIONS: list[set[str]] = []

def _load_skill_data():
    """Memuat data sinonim skill dari JSON."""
    global SYMBOL_NORMALIZATION_MAP, SKILL_SYNONYMS, SKILL_CLUSTERS
    try:
        with open(SKILL_DATA_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        SYMBOL_NORMALIZATION_MAP = data.get("SYMBOL_NORMALIZATION_MAP", {})
        SKILL_SYNONYMS = data.get("SKILL_SYNONYMS", {})
        
        # Konversi array list kembali menjadi list of sets untuk kemudahan lookup
        clusters_raw = data.get("SKILL_CLUSTERS", [])
        SKILL_CLUSTERS = [set(cluster) for cluster in clusters_raw]
        
        exclusions_raw = data.get("SKILL_EXCLUSIONS", [])
        SKILL_EXCLUSIONS = [set(exc) for exc in exclusions_raw]
        
        logger.info("Berhasil memuat skill_synonyms.json")
        
    except Exception as e:
        logger.error(f"Gagal memuat {SKILL_DATA_PATH}: {e}")
        # Default empty fallbacks
        SYMBOL_NORMALIZATION_MAP = {}
        SKILL_SYNONYMS = {}
        SKILL_CLUSTERS = []
        SKILL_EXCLUSIONS = []

# Panggil fungsi load saat modul diimpor
_load_skill_data()


def _apply_symbol_normalization(text: str) -> str:
    """Menerapkan normalisasi simbol pada teks keahlian mentah.

    Mengganti karakter khusus (seperti ++, #, titik pada framework)
    menjadi bentuk alfanumerik sebelum proses lookup sinonim.

    Parameter:
        text (str): Teks keahlian mentah dalam huruf kecil.

    Return:
        str: Teks yang telah dinormalisasi simbolnya.
    """
    for symbol, replacement in SYMBOL_NORMALIZATION_MAP.items():
        if text == symbol:
            return replacement
    return text


def normalize_skill(skill: str) -> str:
    """Menormalisasi string keahlian menggunakan peta simbol dan kamus sinonim.

    Alur normalisasi:
    1. Strip dan lowercase.
    2. Terapkan normalisasi simbol (c++ → cpp, .net → dotnet).
    3. Cocokkan dengan kamus sinonim (reactjs → react).
    4. Jika tidak ditemukan, kembalikan hasil normalisasi simbol apa adanya.

    Parameter:
        skill (str): String keahlian mentah dari CV atau JD.

    Return:
        str: Representasi kanonik dalam huruf kecil, atau string asli jika tidak ditemukan di kamus.
    """
    if not skill:
        return ""
    skill_lower = skill.strip().lower()

    # Tahap 1: Normalisasi simbol
    skill_normalized = _apply_symbol_normalization(skill_lower)

    # Tahap 2: Lookup kamus sinonim (gunakan hasil normalisasi simbol)
    for canonical, synonyms in SKILL_SYNONYMS.items():
        if skill_normalized == canonical or skill_normalized in synonyms:
            return canonical
        # Cek juga input asli (sebelum normalisasi simbol) untuk backward compatibility
        if skill_lower == canonical or skill_lower in synonyms:
            return canonical

    return skill_normalized


def get_skill_synonyms(skill: str) -> list[str]:
    """Mengembalikan semua variasi nama (sinonim) dari suatu keahlian,

    termasuk nama kanoniknya dan nama aslinya dalam huruf kecil.

    Parameter:
        skill (str): Nama keahlian yang akan dicari sinonimnya.

    Return:
        list[str]: Daftar variasi nama keahlian dalam huruf kecil.
    """
    if not skill:
        return []
    
    skill_lower = skill.strip().lower()
    canonical = normalize_skill(skill)
    
    synonyms = {skill_lower, canonical}
    
    if canonical in SKILL_SYNONYMS:
        synonyms.update(s.lower() for s in SKILL_SYNONYMS[canonical])
        
    return list(synonyms)


def are_skills_similar(skill_a: str, skill_b: str) -> bool:
    """Memeriksa apakah dua keahlian berada dalam satu kelompok keahlian sejenis (Skill Cluster) yang sama.

    Parameter:
        skill_a (str): Nama keahlian pertama.
        skill_b (str): Nama keahlian kedua.

    Return:
        bool: True jika kedua keahlian berada di kelompok yang sama, False jika tidak.
    """
    if not skill_a or not skill_b:
        return False
        
    norm_a = normalize_skill(skill_a)
    norm_b = normalize_skill(skill_b)
    
    if not norm_a or not norm_b:
        return False
        
    for cluster in SKILL_CLUSTERS:
        if norm_a in cluster and norm_b in cluster:
            return True
            
    return False


def are_skills_mutually_exclusive(skill_a: str, skill_b: str) -> bool:
    """Memeriksa apakah dua keahlian secara eksplisit dinyatakan berbeda (saling eksklusif).

    Digunakan untuk mencegah false positive pada pencocokan semantik
    (misal: java dan javascript).

    Parameter:
        skill_a (str): Nama keahlian pertama.
        skill_b (str): Nama keahlian kedua.

    Return:
        bool: True jika kedua keahlian terdaftar di daftar pengecualian yang sama.
    """
    if not skill_a or not skill_b:
        return False
        
    norm_a = normalize_skill(skill_a)
    norm_b = normalize_skill(skill_b)
    
    if not norm_a or not norm_b:
        return False
        
    for exclusion_set in SKILL_EXCLUSIONS:
        if norm_a in exclusion_set and norm_b in exclusion_set:
            return True
            
    return False
