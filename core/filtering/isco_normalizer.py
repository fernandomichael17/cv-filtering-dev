"""ISCO Normalizer Layer.

Menangani logika normalisasi judul pekerjaan ke dalam kode ISCO-08 4-digit.
Menggunakan pencocokan kata kunci (Opsi A) dan fallback berbasis kesamaan semantik (Opsi B).
"""

import logging
import os
import re

from app.config import settings
from core.filtering.semantic_matcher import semantic_matcher
from core.utils.taxonomy import (
    TITLE_TO_ISCO,
    JOB_TAXONOMY_PATH,
    LAST_LOADED_TIME,
    load_taxonomy,
)

logger = logging.getLogger(__name__)

# Cache in-memory untuk menyimpan kode ISCO hasil normalisasi
_ISCO_CACHE: dict[str, str] = {}

# Daftar regex alias yang telah dikompilasi sebelumnya untuk optimalisasi kecepatan
_COMPILED_ALIASES: list[tuple[re.Pattern, str]] | None = None


def _check_taxonomy_updates():
    """Melakukan lazy evaluation untuk mendeteksi perubahan pada berkas job_taxonomy.json dan memuat ulang jika perlu."""
    global _ISCO_CACHE, _COMPILED_ALIASES
    if not os.path.exists(JOB_TAXONOMY_PATH):
        return

    current_mtime = os.path.getmtime(JOB_TAXONOMY_PATH)
    from core.utils.taxonomy import LAST_LOADED_TIME
    if current_mtime > LAST_LOADED_TIME:
        logger.info("Mendeteksi perubahan pada job_taxonomy.json. Melakukan hot-reload...")
        load_taxonomy()
        _ISCO_CACHE.clear()
        _COMPILED_ALIASES = None


def _get_compiled_aliases() -> list[tuple[re.Pattern, str]]:
    """Mengompilasi seluruh alias kata kunci taksonomi ke format regex Pattern.

    Return:
        List[Tuple[re.Pattern, str]]: Daftar pasangan objek regex dan kode ISCO.
    """
    global _COMPILED_ALIASES
    if _COMPILED_ALIASES is None:
        _COMPILED_ALIASES = []
        sorted_aliases = sorted(TITLE_TO_ISCO.items(), key=lambda x: len(x[0]), reverse=True)
        for alias, code in sorted_aliases:
            # Skip single-word aliases to prevent catastrophic greedy matching 
            # (e.g., "security" catching "network security", "manager" catching "marketing manager")
            if len(alias.split()) == 1:
                continue

            pattern = re.escape(alias)
            if alias and re.match(r'^\w', alias):
                pattern = r'(?<!\w)' + pattern
            if alias and re.search(r'\w$', alias):
                pattern = pattern + r'(?!\w)'
            try:
                _COMPILED_ALIASES.append((re.compile(pattern), code))
            except re.error:
                continue
    return _COMPILED_ALIASES


def normalize_to_isco(title: str) -> str:
    """Menormalisasi judul pekerjaan/jabatan menjadi kode ISCO-08 4-digit.

    Metode Pencocokan:
    1. Pencocokan eksak pada kamus TITLE_TO_ISCO.
    2. Pencocokan sebagian (partial keyword) dengan kompilasi regex alias.
    3. Fallback pencocokan semantik (Semantic Embedding Matcher) jika pencocokan kata kunci nihil.

    Parameter:
        title (str): Judul pekerjaan/jabatan yang akan dinormalisasi.

    Return:
        str: Kode ISCO-08 4-digit hasil normalisasi, atau "unknown" jika pencocokan gagal.
    """
    if not title:
        return "unknown"

    _check_taxonomy_updates()

    title_lower = title.strip().lower()

    # Cek cache in-memory terlebih dahulu
    if title_lower in _ISCO_CACHE:
        return _ISCO_CACHE[title_lower]

    # 1. Pencocokan eksak
    if title_lower in TITLE_TO_ISCO:
        code = TITLE_TO_ISCO[title_lower]
        _ISCO_CACHE[title_lower] = code
        logger.debug("ISCO [EXACT] '%s' -> %s", title_lower, code)
        return code

    # 2. Pencocokan regex alias sebagian
    for compiled_pattern, code in _get_compiled_aliases():
        if compiled_pattern.search(title_lower):
            _ISCO_CACHE[title_lower] = code
            logger.debug("ISCO [REGEX] '%s' -> %s", title_lower, code)
            return code

    # 3. Fallback ke Opsi B (Semantic Embedding Matcher)
    fallback_code = semantic_matcher.find_best_isco_code(title_lower)
    if fallback_code != "unknown":
        _ISCO_CACHE[title_lower] = fallback_code
        logger.info("ISCO [SEMANTIC FALLBACK] '%s' -> %s (perlu verifikasi manual)", title_lower, fallback_code)
        return fallback_code

    logger.warning("ISCO [GAGAL] Tidak dapat memetakan jabatan '%s' ke kode ISCO manapun", title_lower)
    _ISCO_CACHE[title_lower] = "unknown"
    return "unknown"
