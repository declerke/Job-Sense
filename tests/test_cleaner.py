import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from scrapers.base_scraper import JobData
from pipeline.cleaner import (
    clean_text, normalize_job_type, normalize_experience,
    detect_remote, extract_tags, clean_job, clean_jobs,
)


# ── clean_text ────────────────────────────────────────────────────────────────
def test_clean_text_strips_html():
    assert clean_text("<b>Data Engineer</b>") == "Data Engineer"

def test_clean_text_decodes_entities():
    assert clean_text("Salary &amp; Benefits") == "Salary & Benefits"

def test_clean_text_collapses_whitespace():
    assert clean_text("  hello   world  ") == "hello world"

def test_clean_text_returns_none_for_empty():
    assert clean_text("") is None
    assert clean_text(None) is None


# ── normalize_job_type ────────────────────────────────────────────────────────
@pytest.mark.parametrize("raw,expected", [
    ("Full-Time",   "full-time"),
    ("FULL TIME",   "full-time"),
    ("Part time",   "part-time"),
    ("CONTRACT",    "contract"),
    ("Internship",  "internship"),
    ("intern",      "internship"),
    ("Attachment",  "internship"),
    (None,          None),
])
def test_normalize_job_type(raw, expected):
    assert normalize_job_type(raw) == expected


# ── normalize_experience ──────────────────────────────────────────────────────
@pytest.mark.parametrize("text,expected", [
    ("Junior Data Analyst",           "entry"),
    ("Senior Software Engineer",      "senior"),
    ("Entry-level Graduate position", "entry"),
    ("Mid-level developer",           "mid"),
    ("Director of Engineering",       "executive"),
    (None,                            None),
])
def test_normalize_experience(text, expected):
    assert normalize_experience(text) == expected


# ── detect_remote ─────────────────────────────────────────────────────────────
def test_detect_remote_via_location():
    job = JobData(title="Engineer", source="test", location="Remote")
    assert detect_remote(job) is True

def test_detect_remote_via_description():
    job = JobData(title="Engineer", source="test", description="This is a work from home opportunity.")
    assert detect_remote(job) is True

def test_detect_remote_false_for_onsite():
    job = JobData(title="Engineer", source="test", location="Nairobi, Kenya")
    assert detect_remote(job) is False


# ── extract_tags ──────────────────────────────────────────────────────────────
def test_extract_tags_finds_known_tech():
    desc = "Must know Python, SQL, and Apache Airflow for ETL pipeline work."
    tags = extract_tags(desc)
    assert "python" in tags
    assert "sql" in tags
    assert "airflow" in tags

def test_extract_tags_returns_none_for_empty():
    assert extract_tags(None) is None
    assert extract_tags("") is None


# ── clean_job ─────────────────────────────────────────────────────────────────
def test_clean_job_filters_short_title():
    job = JobData(title="IT", source="test")
    assert clean_job(job) is None

def test_clean_job_normalizes_fields():
    job = JobData(
        title="<b>Data Engineer</b>",
        source="BrighterMonday",
        job_type="Full Time",
        location="  Nairobi  ",
        description="Work with Python and SQL on ETL pipelines.",
    )
    cleaned = clean_job(job)
    assert cleaned.title == "Data Engineer"
    assert cleaned.job_type == "full-time"
    assert cleaned.location == "Nairobi"
    assert "python" in cleaned.tags

def test_clean_jobs_filters_invalids():
    jobs = [
        JobData(title="OK Job Title", source="test"),
        JobData(title="X", source="test"),      # too short → filtered
        JobData(title=None, source="test"),     # None → filtered
    ]
    result = clean_jobs(jobs)
    assert len(result) == 1
    assert result[0].title == "OK Job Title"
