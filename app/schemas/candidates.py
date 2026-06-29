"""Pydantic schemas untuk extraction endpoint."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ExtractionResponse(BaseModel):
    """Respons dari extraction endpoint."""

    status: str
    require_id: int
    message: str


class TagsStatusResponse(BaseModel):
    """Respons status tags kandidat."""

    require_id: int
    has_tags: bool
    cv_tags: Optional[str] = None
    tags: Optional[str] = None
    skills_extracted: bool = False
    hard_skill: Optional[str] = None
    soft_skill: Optional[str] = None
    experience_tags_count: int = 0
    updated_at: Optional[datetime] = None
