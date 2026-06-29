"""Format candidate data as plain text for LLM evaluation.

Only includes work experience descriptions and certifications/training —
fields that already passed hard filter (education, major, experience years)
are NOT sent to the LLM to reduce token usage.
"""


def format_candidate_for_llm(candidate) -> dict[str, str]:
    """Format a single candidate's relevant data as plain text.

    Args:
        candidate: Require ORM object with loaded relationships.

    Returns:
        Dict with 'educations_text', 'experiences_text' and 'certifications_text'.
    """
    from datetime import datetime

    from core.utils.major_mapping import EDU_ID_TO_STR

    # Format educations
    edu_lines = []
    for i, edu in enumerate(candidate.educations, 1):
        institution = getattr(edu, "institutionname", "N/A") or "N/A"
        major = getattr(edu, "major", "N/A") or "N/A"
        edu_id = getattr(edu, "education_id", None)
        level_str = EDU_ID_TO_STR.get(edu_id, "N/A")
        edu_lines.append(f"{i}. {institution} ({level_str}) - {major}")
    
    educations_text = "\n".join(edu_lines) if edu_lines else "Tidak ada data pendidikan."

    # Format work experiences
    exp_lines = []
    for i, exp in enumerate(candidate.work_experiences, 1):
        company = getattr(exp, "companyname", "N/A") or "N/A"
        jobdesk = getattr(exp, "jobdesk", "N/A") or "N/A"
        
        start_date = getattr(exp, "startdate", None)
        end_date = getattr(exp, "enddate", None)
        start_year = getattr(exp, "startyear", None)
        end_year = getattr(exp, "endyear", None)
        
        duration = 0
        if start_date and end_date:
            duration = int((end_date - start_date).days / 30.0)
        elif start_year and end_year:
            duration = (end_year - start_year) * 12
        elif start_year and getattr(exp, "iscurrent", False):
            duration = (datetime.now().year - start_year) * 12

        duration_str = f" ({duration} bulan)" if duration > 0 else ""
        exp_lines.append(f"{i}. {company}{duration_str}: {jobdesk}")

    experiences_text = "\n".join(exp_lines) if exp_lines else "Tidak ada data pengalaman."

    # Format certifications/trainings
    cert_lines = []
    for i, training in enumerate(candidate.trainings, 1):
        name = getattr(training, "trainingname", "N/A") or "N/A"
        organizer = getattr(training, "organizer", None)
        if organizer:
            cert_lines.append(f"{i}. {name} — {organizer}")
        else:
            cert_lines.append(f"{i}. {name}")

    certifications_text = "\n".join(cert_lines) if cert_lines else "Tidak ada sertifikasi/training."

    return {
        "educations_text": educations_text,
        "experiences_text": experiences_text,
        "certifications_text": certifications_text,
    }
