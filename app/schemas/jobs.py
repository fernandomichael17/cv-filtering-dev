"""Pydantic schemas for job postings."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class JobCreate(BaseModel):
    """Request body for creating a new job posting."""

    title: str
    description: Optional[str] = None
    job_vacancy_job_desc: Optional[str] = None
    job_vacancy_job_spec: Optional[str] = None


class JobParseRequest(BaseModel):
    """Request body for triggering job vacancy parsing via LLM."""

    job_vacancy_id: int
    title: Optional[str] = None
    job_vacancy_job_desc: Optional[str] = None
    job_vacancy_job_spec: Optional[str] = None


class ParsedRequirements(BaseModel):
    """Structured requirements parsed from job description by LLM."""

    min_education: str = "S1"
    allowed_majors: list[str] = []
    major_flexibility: str = "flexible"
    min_experience_years: int = 0
    max_experience_years: Optional[int] = None
    preferred_min_experience_years: Optional[int] = None
    preferred_max_experience_years: Optional[int] = None
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    marital_status: Optional[str] = None
    required_skills: list[str] = []
    preferred_skills: list[str] = []
    standardized_title: Optional[str] = None


class JobResponse(BaseModel):
    """Response after creating/retrieving a job posting."""

    job_vacancy_id: int
    title: str
    description: str
    parsed_requirements: Optional[dict] = None
    tags: Optional[list[str]] = None
    parsing_duration_seconds: Optional[float] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class JobListItem(BaseModel):
    """Summary item for job listing."""

    job_vacancy_id: int
    title: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
