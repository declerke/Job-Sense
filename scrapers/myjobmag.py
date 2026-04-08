import logging
import re

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, JobData

logger = logging.getLogger(__name__)

BASE_URL = "https://www.myjobmag.co.ke"


class MyJobMagScraper(BaseScraper):
    SOURCE_NAME = "MyJobMag"

    def scrape(self, max_pages: int = 5) -> list[JobData]:
        jobs: list[JobData] = []

        for page_num in range(1, max_pages + 1):
            url = f"{BASE_URL}/jobs/page/{page_num}" if page_num > 1 else f"{BASE_URL}/jobs/"
            soup = self.fetch_page(url)
            if not soup:
                break

            # MyJobMag uses li.mag-b for job cards
            cards = soup.select("li.mag-b")
            if not cards:
                logger.info(f"[MyJobMag] No cards on page {page_num}, stopping.")
                break

            for card in cards:
                try:
                    title_el = card.select_one("h2 a, h3 a")
                    if not title_el:
                        continue
                    title = title_el.get_text(strip=True)
                    href = title_el.get("href", "")
                    job_url = href if href.startswith("http") else f"{BASE_URL}{href}"
                    external_id = href.rstrip("/").split("/")[-1]

                    jobs.append(JobData(
                        title=title,
                        source=self.SOURCE_NAME,
                        external_id=external_id,
                        location="Kenya",
                        url=job_url,
                    ))
                except Exception as e:
                    logger.debug(f"[MyJobMag] Card parse error: {e}")

            logger.info(f"[MyJobMag] Page {page_num}: {len(cards)} cards")

        logger.info(f"[MyJobMag] Total: {len(jobs)} jobs")
        return jobs
