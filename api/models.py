from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text

from api.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id                   = Column(Integer, primary_key=True, index=True)
    external_id          = Column(String(500), nullable=True)
    title                = Column(String(500), nullable=False)
    company              = Column(String(300), nullable=True)
    location             = Column(String(300), nullable=True)
    description          = Column(Text, nullable=True)
    salary_min           = Column(Float, nullable=True)
    salary_max           = Column(Float, nullable=True)
    salary_currency      = Column(String(10), default="KES")
    job_type             = Column(String(50), nullable=True)
    experience_level     = Column(String(50), nullable=True)
    remote               = Column(Boolean, default=False)
    url                  = Column(String(1000), nullable=True)
    source               = Column(String(100), nullable=False)
    tags                 = Column(Text, nullable=True)
    requirements         = Column(Text, nullable=True)
    posted_date          = Column(DateTime, nullable=True)
    application_deadline = Column(DateTime, nullable=True)
    scraped_at           = Column(DateTime, default=datetime.utcnow)
    is_active            = Column(Boolean, default=True)
    embedding            = Column(Vector(384), nullable=True)


class ScrapeLog(Base):
    __tablename__ = "scrape_logs"

    id               = Column(Integer, primary_key=True, index=True)
    source           = Column(String(100), nullable=False)
    status           = Column(String(20), nullable=True)
    jobs_found       = Column(Integer, default=0)
    jobs_new         = Column(Integer, default=0)
    jobs_updated     = Column(Integer, default=0)
    jobs_embedded    = Column(Integer, default=0)
    error_message    = Column(Text, nullable=True)
    started_at       = Column(DateTime, default=datetime.utcnow)
    finished_at      = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
