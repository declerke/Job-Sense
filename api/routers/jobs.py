import math
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import Job, ScrapeLog
from api.schemas import (
    JobResponse, PaginatedJobsResponse, ScrapeLogResponse,
    SourceStat, StatsResponse,
)

router = APIRouter(prefix="/api", tags=["jobs"])


@router.get("/jobs", response_model=PaginatedJobsResponse)
def list_jobs(
    search:      Optional[str]  = Query(None, description="Search title, company, tags"),
    source:      Optional[str]  = Query(None),
    location:    Optional[str]  = Query(None),
    job_type:    Optional[str]  = Query(None),
    experience:  Optional[str]  = Query(None),
    remote:      Optional[bool] = Query(None),
    page:        int            = Query(1, ge=1),
    per_page:    int            = Query(20, ge=1, le=100),
    db:          Session        = Depends(get_db),
):
    q = db.query(Job).filter(Job.is_active == True)

    if search:
        like = f"%{search}%"
        q = q.filter(
            Job.title.ilike(like) |
            Job.company.ilike(like) |
            Job.tags.ilike(like) |
            Job.description.ilike(like)
        )
    if source:
        q = q.filter(Job.source == source)
    if location:
        q = q.filter(Job.location.ilike(f"%{location}%"))
    if job_type:
        q = q.filter(Job.job_type.ilike(f"%{job_type}%"))
    if experience:
        q = q.filter(Job.experience_level == experience)
    if remote is not None:
        q = q.filter(Job.remote == remote)

    total = q.count()
    pages = math.ceil(total / per_page) if total > 0 else 1
    jobs = q.order_by(desc(Job.scraped_at)).offset((page - 1) * per_page).limit(per_page).all()

    return PaginatedJobsResponse(
        jobs=[JobResponse.model_validate(j) for j in jobs],
        total=total, page=page, pages=pages, per_page=per_page,
    )


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    from fastapi import HTTPException
    job = db.query(Job).filter(Job.id == job_id, Job.is_active == True).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse.model_validate(job)


@router.get("/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    total     = db.query(func.count(Job.id)).scalar()
    active    = db.query(func.count(Job.id)).filter(Job.is_active == True).scalar()
    embedded  = db.query(func.count(Job.id)).filter(Job.embedding != None).scalar()
    remote    = db.query(func.count(Job.id)).filter(Job.remote == True, Job.is_active == True).scalar()
    sources   = db.query(func.count(func.distinct(Job.source))).scalar()
    last_scraped = db.query(func.max(Job.scraped_at)).scalar()
    return StatsResponse(
        total_jobs=total, active_jobs=active, embedded_jobs=embedded,
        remote_jobs=remote, sources=sources, last_scraped=last_scraped,
    )


@router.get("/sources", response_model=list[SourceStat])
def list_sources(db: Session = Depends(get_db)):
    from sqlalchemy import case
    rows = (
        db.query(
            Job.source,
            func.count(Job.id).label("total_jobs"),
            func.sum(case((Job.is_active == True, 1), else_=0)).label("active_jobs"),
            func.sum(case((Job.embedding != None, 1), else_=0)).label("embedded_jobs"),
            func.max(Job.scraped_at).label("last_scraped"),
        )
        .group_by(Job.source)
        .order_by(desc("total_jobs"))
        .all()
    )
    return [SourceStat(
        source=r.source, total_jobs=r.total_jobs,
        active_jobs=r.active_jobs or 0, embedded_jobs=r.embedded_jobs or 0,
        last_scraped=r.last_scraped,
    ) for r in rows]


@router.get("/scrape-logs", response_model=list[ScrapeLogResponse])
def get_scrape_logs(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    logs = (
        db.query(ScrapeLog)
        .order_by(desc(ScrapeLog.started_at))
        .limit(limit)
        .all()
    )
    return [ScrapeLogResponse.model_validate(l) for l in logs]
