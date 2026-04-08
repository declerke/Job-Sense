import logging

from .base_scraper import BaseScraper, JobData

logger = logging.getLogger(__name__)

BASE_URL = "https://careerpointkenya.co.ke"
JOBS_URL = f"{BASE_URL}/jobs"


class CareerPointKenyaScraper(BaseScraper):
    SOURCE_NAME = "CareerPointKenya"

    def scrape(self, max_pages: int = 5) -> list[JobData]:
        jobs: list[JobData] = []

        for page_num in range(1, max_pages + 1):
            url = f"{JOBS_URL}/page/{page_num}/" if page_num > 1 else JOBS_URL
            soup = self.fetch_page(url)
            if not soup:
                break

            cards = soup.select(
                "article.post, div.job-list, div.vacancy-item, "
                "article[class*='job'], li[class*='job']"
            )
            if not cards:
                logger.info(f"[CareerPointKenya] No cards on page {page_num}, stopping.")
                break

            for card in cards:
                try:
                    title_el = card.select_one("h2 a, h3 a, h1 a, a.entry-title")
                    if not title_el:
                        continue
                    title = title_el.get_text(strip=True)
                    href = title_el.get("href", "")
                    job_url = href if href.startswith("http") else f"{BASE_URL}{href}"
                    external_id = href.rstrip("/").split("/")[-1]

                    company_el = card.select_one(".company, .employer, .organization")
                    company = company_el.get_text(strip=True) if company_el else None

                    location_el = card.select_one(".location, .job-location, span[class*='location']")
                    location = location_el.get_text(strip=True) if location_el else "Kenya"

                    deadline_el = card.select_one(".deadline, .closing-date, time[class*='deadline']")
                    deadline_text = deadline_el.get_text(strip=True) if deadline_el else None

                    jobs.append(JobData(
                        title=title,
                        source=self.SOURCE_NAME,
                        external_id=external_id,
                        company=company,
                        location=location,
                        url=job_url,
                    ))
                except Exception as e:
                    logger.debug(f"[CareerPointKenya] Card parse error: {e}")

            logger.info(f"[CareerPointKenya] Page {page_num}: {len(cards)} cards")

        logger.info(f"[CareerPointKenya] Total: {len(jobs)} jobs")
        return jobs
