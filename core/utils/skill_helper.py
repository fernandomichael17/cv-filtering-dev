"""Skill Helper Utility.

Menyediakan fungsi bersama untuk mengumpulkan dan menormalisasi keahlian kandidat
dari tabel candidate_skills, candidate_tags, dan candidate_experience_tags.
"""

import logging
from core.utils.skill_synonyms import normalize_skill

logger = logging.getLogger(__name__)


def build_candidate_skills(candidate) -> set[str]:
    """Mengumpulkan seluruh keahlian kandidat dari tabel baru cv-filtering.

    Sumber Keahlian:
    1. Tabel candidate_skills (hard_skill, soft_skill, bahasa).
    2. Tag pekerjaan dari riwayat pengalaman kerja (candidate_experience_tags).
    3. Tag CV keseluruhan (candidate_tags).

    Catatan: Nama pelatihan/sertifikasi sengaja dikeluarkan dari daftar keahlian ini
    karena dievaluasi secara terpisah pada komponen sertifikasi.

    Parameter:
        candidate (Require): Objek kandidat ORM dari database.

    Return:
        Set[str]: Kumpulan string keahlian kandidat dalam huruf kecil yang telah dinormalisasi.
    """
    skills: set[str] = set()

    # Sumber 1: Tabel candidate_skills (sumber utama)
    skills_obj = getattr(candidate, "candidate_skills", None)
    if skills_obj:
        for cat in ["hard_skill", "soft_skill", "language"]:
            val = getattr(skills_obj, cat, None)
            if val:
                for s in val.split(","):
                    normalized = normalize_skill(s)
                    if normalized:
                        skills.add(normalized)

    # Sumber 2: Tag pekerjaan dari riwayat pengalaman kerja
    for exp in getattr(candidate, "work_experiences", []) or []:
        exp_tags_obj = getattr(exp, "experience_tags", None)
        if exp_tags_obj:
            tags_str = getattr(exp_tags_obj, "tags", None)
            if tags_str:
                for t in tags_str.split(","):
                    normalized = normalize_skill(t)
                    if normalized:
                        skills.add(normalized)

    # Sumber 3: Tag CV keseluruhan
    cv_tags_obj = getattr(candidate, "candidate_tags", None)
    if cv_tags_obj:
        tags_str = getattr(cv_tags_obj, "tags", None)
        if tags_str:
            for t in tags_str.split(","):
                normalized = normalize_skill(t)
                if normalized:
                    skills.add(normalized)

    return skills


def check_skill_matches(skill: str, candidate_skills: set[str]) -> bool:
    """Memeriksa apakah suatu keahlian cocok dengan kumpulan keahlian kandidat.

    Mendukung kecocokan string eksak, kecocokan batas kata (word boundary) untuk singkatan
    pendek (panjang <= 4) guna menghindari false positive, dan substring untuk kata panjang.

    Parameter:
        skill (str): Nama keahlian yang dicari.
        candidate_skills (set[str]): Kumpulan nama keahlian kandidat (yang sudah dinormalisasi).

    Return:
        bool: True jika cocok, False jika tidak cocok.
    """
    skill_lower = normalize_skill(skill)
    if not skill_lower:
        return False

    if skill_lower in candidate_skills:
        return True

    # Untuk kata kunci keahlian pendek, hindari pencocokan substring parsial
    if len(skill_lower) <= 4:
        import re
        pattern = re.compile(rf"\b{re.escape(skill_lower)}\b")
        for cs in candidate_skills:
            if pattern.search(cs):
                return True
        return False

    for cs in candidate_skills:
        if skill_lower in cs or cs in skill_lower:
            return True

    return False


def build_candidate_jobdesk_texts(candidate) -> list[str]:
    """Mengekstrak teks jobdesk non-kosong dari riwayat pengalaman kerja kandidat.

    Digunakan sebagai sumber fallback untuk pencocokan keahlian di scoring layer
    ketika keahlian terstruktur (candidate_skills, experience_tags) tidak tersedia
    atau tidak lengkap.

    Parameter:
        candidate (Require): Objek kandidat ORM dari database.

    Return:
        list[str]: Daftar teks jobdesk yang sudah dibersihkan (tanpa baris kosong).
    """
    texts = []
    for exp in getattr(candidate, "work_experiences", []) or []:
        jobdesk = getattr(exp, "jobdesk", None)
        if jobdesk and jobdesk.strip():
            texts.append(jobdesk.strip())
    return texts
