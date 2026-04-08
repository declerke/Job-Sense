import logging
import sys
import os
from datetime import datetime, timezone

import psycopg2
from psycopg2.extras import execute_values

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import settings
from scrapers.base_scraper import JobData
from scrapers.brightermonday import BrighterMondayScraper
from scrapers.myjobmag import MyJobMagScraper
from scrapers.fuzu import FuzuScraper
from scrapers.adzuna import AdzunaScraper
from scrapers.remoteok import RemoteOKScraper
from scrapers.careerpointkenya import CareerPointKenyaScraper
from scrapers.jobwebkenya import JobWebKenyaScraper
from scrapers.corporatestaffing import CorporateStaffingScraper
from pipeline.cleaner import clean_jobs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
)
logger = logging.getLogger(__name__)

SCRAPER_REGISTRY = {
    "BrighterMonday":    BrighterMondayScraper,
    "MyJobMag":          MyJobMagScraper,
    "Fuzu":              FuzuScraper,
    "Adzuna":            AdzunaScraper,
    "RemoteOK":          RemoteOKScraper,
    "CareerPointKenya":  CareerPointKenyaScraper,
    "JobWebKenya":       JobWebKenyaScraper,
    "CorporateStaffing": CorporateStaffingScraper,
}


def get_connection():
    return psycopg2.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        dbname=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
    )


def upsert_jobs(conn, jobs: list[JobData]) -> tuple[int, int]:
    """Insert or update jobs. Returns (new_count, updated_count)."""
    if not jobs:
        return 0, 0

    sql = """
        INSERT INTO jobs (
            external_id, title, company, location, description,
            salary_min, salary_max, salary_currency,
            job_type, experience_level, remote, url, source, tags,
            requirements, posted_date, application_deadline, scraped_at, is_active
        ) VALUES %s
        ON CONFLICT (source, external_id)
        DO UPDATE SET
            title                = EXCLUDED.title,
            company              = EXCLUDED.company,
            location             = EXCLUDED.location,
            description          = COALESCE(EXCLUDED.description, jobs.description),
            salary_min           = COALESCE(EXCLUDED.salary_min, jobs.salary_min),
            salary_max           = COALESCE(EXCLUDED.salary_max, jobs.salary_max),
            tags                 = COALESCE(EXCLUDED.tags, jobs.tags),
            scraped_at           = EXCLUDED.scraped_at,
            is_active            = TRUE
        RETURNING id, (xmax = 0) AS inserted
    """
    now = datetime.now(timezone.utc)
    # Deduplicate by (source, external_id) before upsert to avoid batch cardinality violations
    seen = set()
    deduped = []
    for j in jobs:
        if not j.title or not (j.external_id or j.url):
            continue
        key = (j.source, j.external_id or j.url)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(j)

    rows = [
        (
            j.external_id or j.url,
            j.title, j.company, j.location, j.description,
            j.salary_min, j.salary_max, j.salary_currency or "KES",
            j.job_type, j.experience_level, j.remote, j.url, j.source, j.tags,
            j.requirements, j.posted_date, j.application_deadline, now, True,
        )
        for j in deduped
    ]

    if not rows:
        return 0, 0

    with conn.cursor() as cur:
        results = execute_values(cur, sql, rows, fetch=True)
        conn.commit()

    new_count = sum(1 for r in results if r[1])
    updated_count = len(results) - new_count
    return new_count, updated_count


def log_scrape(conn, source: str, status: str, jobs_found: int,
               jobs_new: int, jobs_updated: int, started_at: datetime,
               error_message: str = None):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO scrape_logs
              (source, status, jobs_found, jobs_new, jobs_updated, error_message, started_at, finished_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        """, (source, status, jobs_found, jobs_new, jobs_updated, error_message, started_at))
        conn.commit()


def run_scraper(source_name: str, max_pages: int = 5) -> dict:
    scraper_class = SCRAPER_REGISTRY.get(source_name)
    if not scraper_class:
        raise ValueError(f"Unknown source: {source_name}")

    started_at = datetime.now(timezone.utc)
    conn = get_connection()

    try:
        scraper = scraper_class()
        raw_jobs = scraper.scrape(max_pages=max_pages)
        cleaned = clean_jobs(raw_jobs)
        new_count, updated_count = upsert_jobs(conn, cleaned)
        log_scrape(conn, source_name, "success", len(raw_jobs), new_count, updated_count, started_at)

        summary = {
            "source": source_name,
            "status": "success",
            "jobs_found": len(raw_jobs),
            "jobs_cleaned": len(cleaned),
            "jobs_new": new_count,
            "jobs_updated": updated_count,
        }
        logger.info(f"[Runner] {source_name}: {summary}")
        return summary

    except Exception as e:
        logger.error(f"[Runner] {source_name} failed: {e}")
        try:
            conn.rollback()  # clear any aborted transaction before logging
            log_scrape(conn, source_name, "failed", 0, 0, 0, started_at, str(e)[:1000])
        except Exception:
            pass
        return {"source": source_name, "status": "failed", "error": str(e)}
    finally:
        conn.close()


def run_all(max_pages: int = 5) -> list[dict]:
    results = []
    for source in SCRAPER_REGISTRY:
        results.append(run_scraper(source, max_pages=max_pages))
    total = sum(r.get("jobs_new", 0) for r in results)
    logger.info(f"[Runner] All scrapers done. Total new jobs: {total}")
    return results


if __name__ == "__main__":
    run_all(max_pages=3)
