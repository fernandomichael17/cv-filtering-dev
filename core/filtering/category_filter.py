"""Category-based hard filter using tags_jobs category prefix.

Uses the category portion of tags_jobs (e.g. "IT & Software" from "IT & Software, Backend Developer")
to quickly eliminate candidates whose work experience is entirely in an unrelated industry.
"""

import logging

logger = logging.getLogger(__name__)

# ── Category Groups ──────────────────────────────────────────────────────
# Bidang-bidang yang dianggap "serumpun" dikelompokkan bersama.
# Jika kategori pengalaman kandidat dan kategori lowongan berada di GRUP YANG SAMA,
# maka dianggap "mungkin relevan" dan diloloskan ke Layer 2 (ISCO matching).
# Jika TIDAK ADA satupun pengalaman di grup yang sama, kandidat langsung di-reject.

CATEGORY_GROUPS: dict[str, list[str]] = {
    "tech": [
        "IT & Software",
        "Engineering & Manufacturing",
    ],
    "business": [
        "Finance & Accounting",
        "Marketing & PR",
        "HR & General Affairs",
    ],
    "service": [
        "Customer Service",
        "Food & Beverage",
        "Healthcare",
    ],
    "operations": [
        "Operations & Supply Chain",
        "Security & Protection",
    ],
    "creative": [
        "Creative & Design",
        "Marketing & PR",  # Marketing sering overlap dengan creative
    ],
    "tech_creative": [
        "IT & Software",
        "Creative & Design",
    ],
    "education": [
        "Education & Training",
        "Healthcare",  # Riset medis bisa overlap
    ],
    "property": [
        "Engineering & Manufacturing",
        "Legal & Compliance",
        "Sales & Business Development",
        "Finance & Accounting",
        "Administration",
        "IT & Software",
        "Property & Real Estate",
    ],
}

# Reverse lookup: category name -> set of group names
_CATEGORY_TO_GROUPS: dict[str, set[str]] = {}
for group_name, categories in CATEGORY_GROUPS.items():
    for cat in categories:
        cat_lower = cat.lower()
        if cat_lower not in _CATEGORY_TO_GROUPS:
            _CATEGORY_TO_GROUPS[cat_lower] = set()
        _CATEGORY_TO_GROUPS[cat_lower].add(group_name)

# ── Job title to category mapping (from job_postings.tags) ───────────────
# Maps the first tag of a job posting to a category group.
JOB_TAG_TO_CATEGORY: dict[str, str] = {
    "it": "IT & Software",
    "python": "IT & Software",
    "machine learning": "IT & Software",
    "marketing": "Marketing & PR",
    "digital campaigns": "Marketing & PR",
    "hr": "HR & General Affairs",
    "finance": "Finance & Accounting",
    "accounting": "Finance & Accounting",
    "healthcare": "Healthcare",
    "engineering": "Engineering & Manufacturing",
    "design": "Creative & Design",
    "creative": "Creative & Design",
    "customer service": "Customer Service",
    "food": "Food & Beverage",
    "operations": "Operations & Supply Chain",
    "security": "Security & Protection",
    "education": "Education & Training",
    "property": "Property & Real Estate",
    "real estate": "Property & Real Estate",
    "legal": "Legal & Compliance",
}


def get_job_category(job_tags: list[str] | None) -> str | None:
    """Determine the category of a job posting from its tags (supports multiple categories).

    Args:
        job_tags: List of tags from job_postings.tags, e.g. ['IT', 'Machine Learning', 'Python']

    Returns:
        Comma-separated categories, e.g. "Finance & Accounting, IT & Software", or None.
    """
    if not job_tags:
        return None

    matched_categories = []
    for tag in job_tags:
        tag_lower = tag.strip().lower()
        if tag_lower in JOB_TAG_TO_CATEGORY:
            cat = JOB_TAG_TO_CATEGORY[tag_lower]
            if cat not in matched_categories:
                matched_categories.append(cat)
                
    if matched_categories:
        return ", ".join(matched_categories)
    return None


def extract_category_from_tags_str(tags_str: str | None) -> str | None:
    """Extract the category (first part) from a tags_jobs string.

    Args:
        tags_str: e.g. "IT & Software, Backend Developer"

    Returns:
        Category string like "IT & Software", or None.
    """
    if not tags_str:
        return None

    parts = [p.strip() for p in tags_str.split(",")]
    if parts and parts[0]:
        return parts[0]
    return None


def are_categories_compatible(cat_a: str, cat_b: str) -> bool:
    """Check if two categories belong to any common group.

    Args:
        cat_a: Category of candidate experience, e.g. "Food & Beverage"
        cat_b: Category of job posting, e.g. "IT & Software"

    Returns:
        True if they share at least one group, False otherwise.
    """
    groups_a = _CATEGORY_TO_GROUPS.get(cat_a.lower(), set())
    groups_b = _CATEGORY_TO_GROUPS.get(cat_b.lower(), set())

    # If either category is not in our mapping, we can't be sure -> return True (safe)
    if not groups_a or not groups_b:
        return True

    return bool(groups_a & groups_b)


def check_category_compatibility(
    candidate_experiences: list,
    compatible_categories: list[str],
) -> dict:
    """
    Memeriksa apakah ada pengalaman kerja kandidat yang berada di bidang yang kompatibel dengan lowongan.

    Parameter:
        candidate_experiences (list): Daftar objek pengalaman kerja kandidat dari database.
        compatible_categories (list[str]): Daftar kategori industri yang kompatibel dari Job Description (LLM).

    Return:
        dict: Hasil pemeriksaan kompatibilitas beserta alasan logisnya.
    """
    if not compatible_categories:
        return {
            "compatible": True,
            "candidate_categories": [],
            "reason": "Daftar kategori kompatibel kosong. Kandidat diloloskan.",
        }

    candidate_categories = []
    has_compatible = False

    for exp in candidate_experiences:
        exp_tags = getattr(exp, "experience_tags", None)
        if not exp_tags:
            continue

        tags_str = getattr(exp_tags, "tags", None)
        cat = extract_category_from_tags_str(tags_str)
        if cat:
            candidate_categories.append(cat)
            # Check compatibility against any compatible categories
            for comp_cat in compatible_categories:
                if cat.strip().lower() == comp_cat.strip().lower():
                    has_compatible = True
                    break
                if are_categories_compatible(cat, comp_cat):
                    has_compatible = True
                    break

    # If no categories found at all, be safe and pass through
    if not candidate_categories:
        return {
            "compatible": True,
            "candidate_categories": [],
            "reason": "Tidak ada data kategori pada pengalaman kandidat. Diloloskan.",
        }

    if has_compatible:
        return {
            "compatible": True,
            "candidate_categories": candidate_categories,
            "reason": (
                f"Pengalaman kandidat ({', '.join(set(candidate_categories))}) "
                f"kompatibel dengan bidang lowongan ({', '.join(compatible_categories)})."
            ),
        }
    else:
        return {
            "compatible": False,
            "candidate_categories": candidate_categories,
            "reason": (
                f"[Kategori Industri] Seluruh riwayat bidang kerja kandidat ({', '.join(set(candidate_categories))}) "
                f"tidak sejalan dengan bidang lowongan yang dicari ({', '.join(compatible_categories)})."
            ),
        }

