from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = "KES"
    job_type: Optional[str] = None
    experience_level: Optional[str] = None
    remote: bool = False
    url: Optional[str] = None
    source: str
    tags: Optional[str] = None
    posted_date: Optional[datetime] = None
    application_deadline: Optional[datetime] = None
    scraped_at: Optional[datetime] = None


class PaginatedJobsResponse(BaseModel):
    jobs: List[JobResponse]
    total: int
    page: int
    pages: int
    per_page: int


class StatsResponse(BaseModel):
    total_jobs: int
    active_jobs: int
    embedded_jobs: int
    remote_jobs: int
    sources: int
    last_scraped: Optional[datetime] = None


class SourceStat(BaseModel):
    source: str
    total_jobs: int
    active_jobs: int
    embedded_jobs: int
    last_scraped: Optional[datetime] = None


class ScrapeLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    status: Optional[str]
    jobs_found: int
    jobs_new: int
    jobs_updated: int
    jobs_embedded: int
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None


# ── CV Match schemas ──────────────────────────────────────────────────────────

class SkillGap(BaseModel):
    skill: str
    present: bool


class JobMatch(BaseModel):
    job: JobResponse
    similarity_score: float       # raw cosine similarity 0.0–1.0
    match_score: int              # LLM-produced 0–100 score
    strengths: List[str]
    gaps: List[str]
    recommendation: str


class CVMatchResponse(BaseModel):
    cv_summary: str               # first 300 chars of extracted CV text
    matches: List[JobMatch]
    model_used: str
