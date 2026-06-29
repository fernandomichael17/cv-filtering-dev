"""Pydantic schemas for filtering operations."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class EducationInfo(BaseModel):
    """Education summary for a candidate."""

    level: Optional[str] = None
    major: Optional[str] = None
    university: Optional[str] = None


class ExperienceInfo(BaseModel):
    """Work experience summary."""

    job_title: Optional[str] = None
    job_role: Optional[str] = None
    jobdesk: Optional[str] = None
    company: Optional[str] = None
    duration_months: Optional[int] = None


class CertificationInfo(BaseModel):
    """Certification/training summary."""

    name: Optional[str] = None
    issuer: Optional[str] = None


class CandidateResult(BaseModel):
    """Representasi hasil filtering untuk satu kandidat."""

    candidate_id: int
    name: str
    tags: Optional[str] = None
    education: Optional[EducationInfo] = None
    experiences: list[ExperienceInfo] = []
    certifications: list[CertificationInfo] = []
    similarity_score: Optional[float] = None
    match_reason: Optional[str] = None
    total_score: float = 0.0
    score_before_adjustment: Optional[float] = None
    llm_confidence: Optional[str] = None
    score_breakdown: Optional[dict] = None
    is_alternative: Optional[bool] = False
    decision: Optional[str] = None
    confidence: Optional[str] = None  # "high", "medium", "low" — tingkat keyakinan sistem


class FilteringResponse(BaseModel):
    """Full response from the filtering pipeline."""

    job_vacancy_id: int
    job_tags: Optional[list[str]] = None
    total_candidates: int
    after_hard_filter: int
    after_skills_filter: int = 0
    after_taxonomy_filter: int
    duration_seconds: float
    last_batch_processed: Optional[datetime] = None
    candidates: list[CandidateResult] = []


class EliminatedCandidate(BaseModel):
    """A candidate that was eliminated during filtering."""

    stage: str
    candidate_name: str
    reason: Optional[str] = None


class DirectFilteringResponse(BaseModel):
    """Response from direct parsing and filtering pipeline with latency breakdown."""

    job_vacancy_id: int
    job_title: str
    job_tags: Optional[list[str]] = None
    total_candidates: int
    after_hard_filter: int
    after_skills_filter: int = 0
    after_taxonomy_filter: int
    
    # Latency Breakdown
    parsing_duration_seconds: float
    filtering_duration_seconds: float
    total_duration_seconds: float
    
    last_batch_processed: Optional[datetime] = None
    candidates: list[CandidateResult] = []


class FilterTaskResponse(BaseModel):
    """Respon status instan untuk tugas penyaringan latar belakang (background task)."""

    job_vacancy_id: int
    status: str
    message: str

