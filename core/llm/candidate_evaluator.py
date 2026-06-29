"""Candidate Evaluator — LLM-based confidence validation for finalists.

Memvalidasi keakuratan hasil semantic matching dan taxonomy matching
menggunakan LLM. Output berupa confidence flag (high/medium/low) yang
diterjemahkan menjadi penalti skor deterministik, serta alasan kontekstual
dalam Bahasa Indonesia.
"""

import json
import logging
from core.llm.client import call_llm, strip_thinking

logger = logging.getLogger(__name__)

# ── Konstanta Penalti Deterministik ──────────────────────────────────────────

PENALTY_MULTIPLIER = {
    "high": 0.0,
    "medium": 0.15,
    "low": 0.30,
}

# ── Prompt Validasi Confidence ───────────────────────────────────────────────

CONFIDENCE_EVAL_PROMPT = """You are an HR Validation Specialist. Your task is to verify whether the automated skill/role matching results are genuinely accurate for a candidate.

### TARGET JOB CONTEXT
Target Job: {job_title}
Minimum Experience Required: {min_experience_years} years
Job Description (summary): {job_description_short}

### TASK
Evaluate if the automated matching results are genuinely accurate. Focus ONLY on these criteria:
1. Are the matched skills truly relevant to the target job, or are they coincidental string matches? The matched skills are already verified to exist in the candidate's profile.
2. Does the candidate have ANY work experience in a role that is directly or closely related to the target job? A candidate who transitioned from an unrelated role to a relevant role is still valid.
3. If the candidate's most recent or second-most-recent role is relevant, the match should be considered valid even if older roles are unrelated.

### IMPORTANT RULES:
- Do NOT evaluate if the candidate meets the "Minimum Experience Required". The automated system has ALREADY filtered out candidates who do not meet the duration requirement. Your ONLY job is to evaluate the RELEVANCE of their past roles and skills, NOT how long they worked.
- Do NOT penalize candidates for having previous unrelated roles. Career transitions are normal.
- CRITICAL FOR ENTRY-LEVEL (0 YEARS EXP): If minimum experience is 0 years, candidates are NOT expected to have prior work experience.
  * If the candidate has ZERO work experience (empty experience list), you MUST NOT assign "low". Give them "medium" or "high" based on their matched skills.
  * If the candidate has experience in a slightly different but adjacent domain (e.g., Recruitment applying for HR Operation), give them "high" or "medium".
  * Do NOT apply strict senior-level exact-match standards for 0-year requirement jobs.
- Focus on whether the candidate has skills and experience relevant to the target job, not whether the experience is "comprehensive" or "advanced".
- CRITICAL (HIDDEN TITLE RULE): The candidate's listed Work Experience title (e.g., 'Staf', 'Intern', 'Supervisor') is often just a generic corporate rank, NOT their actual profession. You MUST read their 'Jobdesk' description to deduce their TRUE profession. If the Jobdesk describes Software Engineering duties (e.g., Java/Python), evaluate them as a Software Engineer, ignoring the generic title.

### FEW-SHOT EXAMPLES:

Example 1 (Junior/Fresh Graduate Role):
- Target Job: Junior Web Developer
- Minimum Experience Required: 0 years
- Job Description: Build and maintain web applications using Python or Javascript.
- Candidate Profile:
  - Work Experience: [No work experience]
- Automated Matching Results:
  - Taxonomy Match Type: skills_match
  - Required Skills Matched: JavaScript, HTML, CSS
  - Preferred Skills Matched: Python
- Response: {{"confidence": "high", "reason": "Fresh graduate dengan keahlian pemrograman sangat relevan."}}

Example 2 (Adjacent/Overlap Domain):
- Target Job: Tax Accountant
- Minimum Experience Required: 2 years
- Job Description: Manage tax filing, compliance, and financial reports.
- Candidate Profile:
  - Work Experience: Experience 1: Corporate Finance Staff at PT Maju (1.5 years)
- Automated Matching Results:
  - Taxonomy Match Type: related
  - Required Skills Matched: corporate finance, Excel
  - Preferred Skills Matched: accounting
- Response: {{"confidence": "medium", "reason": "Latar belakang finansial beririsan dengan akuntansi umum."}}

Example 3 (Irrelevant Career Transition Attempt):
- Target Job: Civil Engineer
- Minimum Experience Required: 3 years
- Job Description: Structural analysis and construction site management.
- Candidate Profile:
  - Work Experience: Experience 1: Content Creator at Youtube (3 years)
- Automated Matching Results:
  - Taxonomy Match Type: unrelated
  - Required Skills Matched: None
  - Preferred Skills Matched: None
- Response: {{"confidence": "low", "reason": "Pengalaman content creator tidak relevan dengan teknik sipil."}}

### CONFIDENCE LEVEL DEFINITIONS
- "high": Matched skills are genuinely relevant AND candidate has experience (including internship/project for entry-level) in a related role AND at least half of the required skills are matched.
- "medium": Matched skills are relevant but candidate's related experience is limited, indirect, OR stems from an adjacent/broader professional field (e.g., Corporate Finance applying for Accounting, Civil Engineering applying for Architecture, or B2B Sales applying for Digital Marketing). Also use "medium" if less than half of the required skills are matched. Do NOT assign "low" to experienced professionals coming from a closely overlapping industry field.
- "low": Matched skills are coincidental/surface-level matches. Candidate has NO experience in any related or overlapping role. Use this ONLY for completely irrelevant career backgrounds (e.g., Content Creator applying for Construction Engineering, or General Admin applying for Advanced Medical roles). CRITICAL: Do NOT assign "low" to candidates transitioning within the same broad sector (e.g., IT Support to DevOps/Software, or Admin to HR). This deserves at least "medium".

### CRITICAL RULE FOR REASONING TEXT:
- Do NOT use reductive or dismissive phrases like "hanya [unrelated role]" (e.g., "hanya Admin", "hanya Support") if the candidate possesses other, more specialized or relevant experiences in their chronological history. 
- You MUST acknowledge the highest-level or most relevant experience they possess in your reason, even if it doesn't perfectly match the exact target specialization. For example: "Pengalaman finansial umum, bukan spesifik akuntansi pajak."
- ATTENTION RESCUE (FOR SMALL LLMS): When evaluating multiple experiences, do NOT average them out or label the candidate as "dominan di [Unrelated Role]" if they clearly have at least one highly relevant role in their history. Evaluate them based on their MOST RELEVANT role.

====================================================
### CANDIDATE EVALUATION

Candidate Profile:
- Work Experience (chronological): {experience}

Automated Matching Results (verified by system):
- Taxonomy Match Type: {match_type}
- Required Skills Matched: {matched_required}
- Preferred Skills Matched: {matched_preferred}

Respond in this exact JSON format (no markdown fences, no extra text):
{{"confidence": "high|medium|low", "reason": "1 kalimat ringkas dalam Bahasa Indonesia (maksimal 6-9 kata)"}}

Response:"""


def _parse_confidence_response(raw_text: str) -> dict:
    """Mengekstrak dan memvalidasi respons JSON confidence dari output LLM.

    Parameter:
        raw_text (str): Teks mentah dari respons LLM.

    Return:
        dict: Dictionary berisi 'confidence' (str) dan 'reason' (str).
              Jika parsing gagal, mengembalikan confidence 'medium' sebagai default aman.
    """
    try:
        clean = strip_thinking(raw_text).strip()
        # Bersihkan markdown code fences jika ada
        clean = clean.replace("```json", "").replace("```", "").strip()

        # Cari pola JSON di dalam teks
        start = clean.find("{")
        end = clean.rfind("}") + 1
        if start >= 0 and end > start:
            json_str = clean[start:end]
            data = json.loads(json_str)

            confidence = data.get("confidence", "medium").lower().strip()
            reason = data.get("reason", "Evaluasi otomatis tidak tersedia.")

            # Validasi confidence value
            if confidence not in ("high", "medium", "low"):
                logger.warning(
                    "Nilai confidence tidak valid dari LLM: '%s', fallback ke 'medium'",
                    confidence,
                )
                confidence = "medium"

            return {"confidence": confidence, "reason": str(reason)}

    except (json.JSONDecodeError, ValueError, TypeError) as e:
        logger.warning("Gagal parsing JSON confidence dari LLM: %s", e)

    # Default fallback yang aman — tidak menghukum kandidat jika LLM gagal
    return {
        "confidence": "medium",
        "reason": "Evaluasi otomatis tidak tersedia karena kendala teknis.",
    }


async def evaluate_candidate_confidence(
    candidate_id: int,
    experience: str,
    job_title: str,
    job_description: str,
    match_type: str,
    matched_required: str,
    matched_preferred: str,
    min_experience_years: float = 0.0,
) -> dict:
    """Memvalidasi keakuratan hasil semantic/taxonomy matching menggunakan LLM.

    Mengirimkan profil pengalaman kerja kandidat beserta hasil matching otomatis ke LLM,
    lalu meminta evaluasi confidence (high/medium/low) terhadap keakuratan matching.
    Confidence flag kemudian diterjemahkan menjadi penalti skor deterministik.
    Data skills kandidat tidak dikirim secara terpisah karena sudah tercakup dalam
    matched_required dan matched_preferred yang sudah diverifikasi oleh sistem.

    Parameter:
        candidate_id (int): ID unik kandidat.
        experience (str): Ringkasan riwayat pengalaman kerja kandidat (jabatan dan durasi).
        job_title (str): Judul posisi lowongan pekerjaan.
        job_description (str): Teks deskripsi pekerjaan (dipotong max 300 karakter).
        match_type (str): Tipe taxonomy match (exact/related/loosely_related/skills_match).
        matched_required (str): Daftar required skills yang berhasil di-match.
        matched_preferred (str): Daftar preferred skills yang berhasil di-match.
        min_experience_years (float): Batas minimum pengalaman kerja yang diminta lowongan (0 = entry-level).

    Return:
        dict: Dictionary berisi:
            - 'confidence' (str): Level confidence (high/medium/low).
            - 'reason' (str): Alasan evaluasi dalam Bahasa Indonesia.
            - 'penalty_multiplier' (float): Pengali penalti proporsional (0.0, 0.15, atau 0.30).
    """
    # Potong deskripsi agar tidak membebani token budget
    job_desc_short = job_description[:300] + "..." if len(job_description) > 300 else job_description

    prompt = CONFIDENCE_EVAL_PROMPT.format(
        job_title=job_title,
        min_experience_years=min_experience_years,
        job_description_short=job_desc_short,
        experience=experience,
        match_type=match_type,
        matched_required=matched_required or "Tidak ada",
        matched_preferred=matched_preferred or "Tidak ada",
    )

    messages = [{"role": "user", "content": prompt}]

    try:
        raw_response = await call_llm(messages, max_tokens=256, temperature=0.1)
        result = _parse_confidence_response(raw_response)

        penalty_multiplier = PENALTY_MULTIPLIER.get(result["confidence"], 0.15)
        result["penalty_multiplier"] = penalty_multiplier

        logger.info(
            "Confidence validation untuk kandidat #%d: %s (pengali penalti: %s) — %s",
            candidate_id,
            result["confidence"],
            penalty_multiplier,
            result["reason"],
        )

        return result

    except Exception as e:
        logger.error("Gagal mengevaluasi confidence kandidat #%d: %s", candidate_id, e)
        return {
            "confidence": "medium",
            "reason": "Evaluasi gagal karena kendala teknis pada server AI.",
            "penalty_multiplier": PENALTY_MULTIPLIER["medium"],
        }
