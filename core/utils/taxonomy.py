"""Taxonomy dictionary and mapping loader.

Loads official ISCO-08 codes and manually defined Indonesian/English job aliases
from job_taxonomy.json, and automatically injects synonyms from thesaurus_taxonomy.json.
Provides TITLE_TO_ISCO mapping.
"""

import json
import logging
import os

# Trigger reload
logger = logging.getLogger(__name__)

# File Paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
JOB_TAXONOMY_PATH = os.path.join(CURRENT_DIR, "data", "job_taxonomy.json")
ESCO_TAXONOMY_PATH = os.path.join(CURRENT_DIR, "data", "esco_taxonomy.json")
THESAURUS_TAXONOMY_PATH = os.path.join(CURRENT_DIR, "data", "thesaurus_taxonomy.json")

# Initialize backward-compatible variables
BASE_ISCO = {}
KBJI_ALIASES = {}
TITLE_TO_ISCO = {}
LAST_LOADED_TIME = 0.0

def load_taxonomy():
    global BASE_ISCO, KBJI_ALIASES, TITLE_TO_ISCO, LAST_LOADED_TIME
    BASE_ISCO.clear()
    KBJI_ALIASES.clear()
    TITLE_TO_ISCO.clear()
    
    import time
    LAST_LOADED_TIME = time.time()


    # 1. Load job_taxonomy.json (contains both BASE_ISCO names and manual KBJI_ALIASES)
    if os.path.exists(JOB_TAXONOMY_PATH):
        try:
            with open(JOB_TAXONOMY_PATH, "r", encoding="utf-8") as f:
                job_taxonomy = json.load(f)
            
            for code, data in job_taxonomy.items():
                name = data.get("name", "")
                aliases = data.get("aliases", [])
                
                # Populate backward-compatible dicts
                BASE_ISCO[code] = name
                if aliases:
                    KBJI_ALIASES[code] = aliases
                    
                # Populate main TITLE_TO_ISCO mapping
                if name:
                    TITLE_TO_ISCO[name.lower().strip()] = code
                for alias in aliases:
                    if alias:
                        TITLE_TO_ISCO[alias.lower().strip()] = code
            
            logger.info(f"Successfully loaded {len(job_taxonomy)} taxonomy codes with {len(TITLE_TO_ISCO)} base titles/aliases.")
        except Exception as e:
            logger.error(f"Error loading job_taxonomy.json: {e}")
    else:
        logger.warning(f"job_taxonomy.json not found at {JOB_TAXONOMY_PATH}!")

    # 2. Load esco_taxonomy.json (contains detailed ESCO occupations mapped to ISCO codes)
    if os.path.exists(ESCO_TAXONOMY_PATH):
        try:
            with open(ESCO_TAXONOMY_PATH, "r", encoding="utf-8") as f:
                esco_data = json.load(f)
                
            esco_injected = 0
            for title, code in esco_data.items():
                title_clean = title.lower().strip()
                # Do NOT overwrite existing mappings from job_taxonomy.json
                if title_clean not in TITLE_TO_ISCO:
                    TITLE_TO_ISCO[title_clean] = code
                    esco_injected += 1
                    
            logger.info(f"Successfully loaded {esco_injected} ESCO occupations into TITLE_TO_ISCO.")
        except Exception as e:
            logger.error(f"Error loading esco_taxonomy.json: {e}")
    else:
        logger.warning(f"esco_taxonomy.json not found at {ESCO_TAXONOMY_PATH}!")

    # 3. Automatically inject modern synonyms from thesaurus_taxonomy.json
    if os.path.exists(THESAURUS_TAXONOMY_PATH):
        try:
            with open(THESAURUS_TAXONOMY_PATH, "r", encoding="utf-8") as f:
                thesaurus_data = json.load(f)
                
            injected_count = 0
            for canonical, synonyms in thesaurus_data.items():
                # Clean canonical key (replace underscores with spaces, lowercase, strip)
                clean_canonical = canonical.replace('_', ' ').lower().strip()
                
                # Step A: Check for exact match in current TITLE_TO_ISCO mapping
                code = TITLE_TO_ISCO.get(clean_canonical)
                
                # Step B: If no exact match, perform an O(1) word-suffix lookup
                # e.g., "senior software engineer" -> check "software engineer", then "engineer"
                if not code:
                    words = clean_canonical.split()
                    # Check suffixes of length N-1 down to 1
                    for i in range(1, len(words)):
                        suffix = " ".join(words[i:])
                        if len(suffix) > 3:  # Skip short suffixes like "it", "qa"
                            code = TITLE_TO_ISCO.get(suffix)
                            if code:
                                break
                
                # Step C: If mapped to a valid code, inject all synonyms
                if code:
                    for syn in synonyms:
                        syn_clean = syn.lower().strip()
                        if syn_clean and syn_clean not in TITLE_TO_ISCO:
                            TITLE_TO_ISCO[syn_clean] = code
                            injected_count += 1
            
            logger.info(f"Successfully injected {injected_count} modern synonyms into TITLE_TO_ISCO.")
        except Exception as e:
            logger.error(f"Error loading thesaurus_taxonomy.json: {e}")
    else:
        logger.warning(f"thesaurus_taxonomy.json not found at {THESAURUS_TAXONOMY_PATH}!")



    # 5. Handle IT Group specific mappings
    for title, code in list(TITLE_TO_ISCO.items()):
        if code.startswith("25"):
            if "developer" in title or "programmer" in title or "engineer" in title:
                if title not in TITLE_TO_ISCO:
                    TITLE_TO_ISCO[title] = code

# Eksekusi pertama kali saat modul di-load
load_taxonomy()
