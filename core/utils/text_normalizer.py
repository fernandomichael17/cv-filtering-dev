"""Utilitas untuk membersihkan teks, menangani salah ketik (typo), dan menyamakan sinonim."""

import logging
try:
    from rapidfuzz import fuzz, process
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False

logger = logging.getLogger(__name__)

# Kamus Mikro (Dictionary Patch) untuk anomali mutlak
# Kata harus di-lowercase. Kamus ini akan di-update jika HRD melaporkan kata yang sering gagal terbaca.
DICTIONARY_PATCH = {
    # IT & Software
    "go": "golang",
    "react.js": "reactjs",
    "react. js": "reactjs",
    "node.js": "nodejs",
    "vue.js": "vuejs",
    "aws": "amazon web services",
    "gcp": "google cloud platform",
    "js": "javascript",
    "ts": "typescript",
    "ui/ux": "user interface user experience",
    "k8s": "kubernetes",
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "fe": "frontend",
    "be": "backend",
    
    # HR & Business
    "k3": "keselamatan dan kesehatan kerja",
    "hse": "keselamatan dan kesehatan kerja",
    "pic": "person in charge",
    "qa": "quality assurance",
    "qc": "quality control",
    "hr": "human resources",
    "hrd": "human resources department",
    "pr": "public relations",
    "pm": "project manager",
    
    # Marketing & Design
    "seo": "search engine optimization",
    "sem": "search engine marketing",
    "kol": "key opinion leader",
    "socmed": "social media",
    
    # Common Typos
    "digtal": "digital",
    "maintanance": "maintenance",
    "maintance": "maintenance",
}


def normalize_text(query: str, known_targets: list[str] = None, threshold: float = 90.0) -> str:
    """
    Membersihkan teks dari salah ketik dan mencocokkan sinonim mutlak.
    
    Langkah:
    1. Cek di DICTIONARY_PATCH untuk penggantian eksak.
    2. Gunakan RapidFuzz untuk mencari kemiripan ejaan di dalam `known_targets`.
       Hanya dilakukan jika query cukup panjang (> 4 huruf) untuk mencegah over-correction.
    
    Parameter:
        query: Teks yang akan dinormalisasi (contoh: "digtal revenue officer").
        known_targets: Daftar teks standar yang valid.
        threshold: Batas minimal skor RapidFuzz (0-100) untuk dianggap sama.
        
    Return:
        String yang sudah dinormalisasi.
    """
    if not query:
        return query
        
    query_clean = query.strip().lower()
    
    # 1. Exact Dictionary Match
    if query_clean in DICTIONARY_PATCH:
        return DICTIONARY_PATCH[query_clean]
        
    # 2. Fuzzy String Matching (RapidFuzz)
    # Gunakan fuzzy match HANYA jika:
    # - Library terinstal
    # - Ada daftar target yang dituju
    # - Panjang query > 4 (mencegah "java" direplace jadi "jaya")
    if HAS_RAPIDFUZZ and known_targets and len(query_clean) > 4:
        # process.extractOne mengembalikan tuple (best_match, score, index)
        match = process.extractOne(query_clean, known_targets, scorer=fuzz.ratio)
        if match:
            best_match, score, _ = match
            if score >= threshold:
                logger.debug(f"[Text Normalizer] Typo fixed: '{query_clean}' -> '{best_match}' (score: {score:.2f})")
                return best_match
                
    return query_clean
