import logging
import time
from datetime import datetime

from .base_scraper import BaseScraper, JobData

logger = logging.getLogger(__name__)

API_URL = "https://remoteok.com/api"

# Tags that signal relevance for a data engineering portfolio context
RELEVANT_TAGS = {
    "python", "data", "sql", "backend", "devops", "aws", "gcp", "azure",
    "kafka", "spark", "airflow", "postgres", "analytics", "machine-learning",
    "api", "engineering", "django", "fastapi", "nodejs", "golang",
}


class RemoteOKScraper(BaseScraper):
    SOURCE_NAME = "RemoteOK"

    def scrape(self, max_pages: int = 5) -> list[JobData]:
        # RemoteOK returns all jobs in a single JSON response (no pagination)
        headers = {"User-Agent": "Mozilla/5.0 (compatible; JobSense/1.0)"}
        data = self.fetch_json(API_URL, headers=headers)

        if not data or not isinstance(data, list):
            logger.warning("[RemoteOK] No data returned from API.")
            return []

        jobs: list[JobData] = []
        # First item is a legal notice dict, skip it
        for item in data[1:]:
            if not isinstance(item, dict):
                continue
            try:
                item_tags = {t.lower() for t in item.get("tags", [])}
                # Only include jobs with at least one relevant tag
                if not item_tags.intersection(RELEVANT_TAGS):
                    continue

                title = item.get("position", "").strip()
                if not title:
                    continue

                posted_raw = item.get("date")
                posted_date = None
                if posted_raw:
                    try:
                        posted_date = datetime.fromisoformat(posted_raw.replace("Z", "+00:00"))
                    except ValueError:
                        pass

                jobs.append(JobData(
                    title=title,
                    source=self.SOURCE_NAME,
                    external_id=str(item.get("id", "")),
                    company=item.get("company"),
                    location="Remote",
                    description=item.get("description"),
                    remote=True,
                    url=item.get("url"),
                    tags=",".join(item.get("tags", [])),
                    posted_date=posted_date,
                ))
            except Exception as e:
                logger.debug(f"[RemoteOK] Item parse error: {e}")

        logger.info(f"[RemoteOK] Total relevant: {len(jobs)} jobs")
        return jobs
