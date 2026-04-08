import html
import logging
import re
from typing import Optional

from scrapers.base_scraper import JobData

logger = logging.getLogger(__name__)

TECH_TAGS = [
    "python", "sql", "java", "javascript", "typescript", "go", "scala", "r",
    "react", "node.js", "django", "flask", "fastapi", "spring",
    "docker", "kubernetes", "terraform", "ansible",
    "aws", "gcp", "azure", "bigquery", "snowflake", "redshift",
    "postgresql", "mysql", "mongodb", "redis", "cassandra", "elasticsearch",
    "kafka", "spark", "flink", "airflow", "dbt", "luigi",
    "tableau", "power bi", "looker", "grafana", "metabase",
    "machine learning", "deep learning", "nlp", "computer vision",
    "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch",
    "git", "ci/cd", "jenkins", "github actions",
    "etl", "data pipeline", "data warehouse", "data lake",
    "rest api", "graphql", "microservices",
    "linux", "bash", "excel", "accounting", "finance",
]

JOB_TYPE_MAP = {
    "full-time": "full-time", "full time": "full-time", "fulltime": "full-time",
    "part-time": "part-time", "part time": "part-time", "parttime": "part-time",
    "contract": "contract", "contractor": "contract",
    "freelance": "freelance",
    "temporary": "temporary", "temp": "temporary",
    "internship": "internship", "intern": "internship", "attachment": "internship",
    "volunteer": "volunteer",
}

EXPERIENCE_MAP = {
    ("entry", "junior", "jr", "graduate", "fresh", "0-1", "0-2"): "entry",
    ("mid", "intermediate", "associate", "2-4", "3-5"): "mid",
    ("senior", "sr", "lead", "principal", "5+", "6+"): "senior",
    ("executive", "director", "head", "vp", "c-level", "chief"): "executive",
}

REMOTE_KEYWORDS = {"remote", "work from home", "wfh", "anywhere", "distributed", "worldwide"}


def clean_text(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def normalize_job_type(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    raw_lower = raw.lower().strip()
    for key, value in JOB_TYPE_MAP.items():
        if key in raw_lower:
            return value
    return raw_lower


def normalize_experience(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    lower = text.lower()
    for keywords, level in EXPERIENCE_MAP.items():
        if any(k in lower for k in keywords):
            return level
    return None


def detect_remote(job: JobData) -> bool:
    combined = " ".join(filter(None, [job.title, job.location, job.description])).lower()
    return any(kw in combined for kw in REMOTE_KEYWORDS)


def extract_tags(description: Optional[str]) -> Optional[str]:
    if not description:
        return None
    lower = description.lower()
    found = [tag for tag in TECH_TAGS if tag in lower]
    return ",".join(found) if found else None


def normalize_salary_currency(job: JobData) -> JobData:
    if job.salary_min or job.salary_max:
        if not job.salary_currency:
            loc = (job.location or "").lower()
            if any(k in loc for k in ["kenya", "nairobi", "mombasa", "kisumu"]):
                job.salary_currency = "KES"
            elif any(k in loc for k in ["remote", "worldwide", "anywhere", "global"]):
                job.salary_currency = "USD"
            else:
                job.salary_currency = "KES"
    return job


def clean_job(job: JobData) -> Optional[JobData]:
    job.title = clean_text(job.title)
    job.company = clean_text(job.company)
    job.location = clean_text(job.location)
    job.description = clean_text(job.description)

    if not job.title or len(job.title) < 5:
        return None

    # Normalize categorical fields
    job.job_type = normalize_job_type(job.job_type)
    if not job.experience_level:
        job.experience_level = normalize_experience(
            (job.title or "") + " " + (job.description or "")
        )

    # Detect remote
    if not job.remote:
        job.remote = detect_remote(job)

    # Extract tags from description if absent
    if not job.tags and job.description:
        job.tags = extract_tags(job.description)

    job = normalize_salary_currency(job)

    if job.url:
        job.url = job.url.strip()

    return job


def clean_jobs(jobs: list[JobData]) -> list[JobData]:
    cleaned = [clean_job(j) for j in jobs]
    result = [j for j in cleaned if j is not None]
    logger.info(f"[Cleaner] {len(result)}/{len(jobs)} jobs passed cleaning")
    return result
