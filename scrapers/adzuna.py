import logging
from datetime import datetime

from .base_scraper import BaseScraper, JobData
from config.settings import settings

logger = logging.getLogger(__name__)

API_BASE = "https://api.adzuna.com/v1/api/jobs/ke/search"


class AdzunaScraper(BaseScraper):
    SOURCE_NAME = "Adzuna"

    def scrape(self, max_pages: int = 5) -> list[JobData]:
        _id = settings.ADZUNA_APP_ID or ""
        _key = settings.ADZUNA_APP_KEY or ""
        if not _id or not _key or _id.startswith("your_") or _key.startswith("your_"):
            logger.warning(
                "[Adzuna] No valid API credentials — skipping. "
                "Register for free at https://developer.adzuna.com to get APP_ID and APP_KEY."
            )
            return []

        jobs: list[JobData] = []

        for page_num in range(1, max_pages + 1):
            url = f"{API_BASE}/{page_num}"
            params = {
                "app_id": settings.ADZUNA_APP_ID,
                "app_key": settings.ADZUNA_APP_KEY,
                "results_per_page": 50,
                "what": "data engineer OR data analyst OR software developer",
                "where": "kenya",
                "content-type": "application/json",
            }
            data = self.fetch_json(url, params=params)
            if not data or "results" not in data:
                break

            results = data["results"]
            if not results:
                break

            for item in results:
                try:
                    title = item.get("title", "").strip()
                    if not title:
                        continue

                    salary_min = item.get("salary_min")
                    salary_max = item.get("salary_max")

                    posted_raw = item.get("created")
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
                        company=item.get("company", {}).get("display_name"),
                        location=item.get("location", {}).get("display_name", "Kenya"),
                        description=item.get("description"),
                        salary_min=float(salary_min) if salary_min else None,
                        salary_max=float(salary_max) if salary_max else None,
                        salary_currency="KES",
                        url=item.get("redirect_url"),
                        posted_date=posted_date,
                    ))
                except Exception as e:
                    logger.debug(f"[Adzuna] Item parse error: {e}")

            logger.info(f"[Adzuna] Page {page_num}: {len(results)} jobs")

        logger.info(f"[Adzuna] Total: {len(jobs)} jobs")
        return jobs
