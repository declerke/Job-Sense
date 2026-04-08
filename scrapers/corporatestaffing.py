import logging

from .base_scraper import BaseScraper, JobData

logger = logging.getLogger(__name__)

BASE_URL = "https://www.corporatestaffing.co.ke"
JOBS_URL = f"{BASE_URL}/jobs"


class CorporateStaffingScraper(BaseScraper):
    SOURCE_NAME = "CorporateStaffing"

    def scrape(self, max_pages: int = 5) -> list[JobData]:
        jobs: list[JobData] = []

        for page_num in range(1, max_pages + 1):
            url = f"{JOBS_URL}/page/{page_num}/" if page_num > 1 else f"{JOBS_URL}/"
            soup = self.fetch_page(url)
            if not soup:
                break

            # Corporate Staffing uses WordPress: cards are div.entry-content-wrap
            cards = soup.select("div.entry-content-wrap")
            if not cards:
                logger.info(f"[CorporateStaffing] No cards on page {page_num}, stopping.")
                break

            for card in cards:
                try:
                    title_el = card.select_one("h2.entry-title a, h2 a, h3 a")
                    if not title_el:
                        continue
                    title = title_el.get_text(strip=True)
                    href = title_el.get("href", "")
                    job_url = href if href.startswith("http") else f"{BASE_URL}{href}"
                    external_id = href.rstrip("/").split("/")[-1]

                    # Category links contain the job category (used as company proxy)
                    cat_el = card.select_one(".category-links a, .entry-taxonomies a")
                    company = cat_el.get_text(strip=True) if cat_el else "Corporate Staffing Services"

                    # Date
                    date_el = card.select_one("time.entry-date")
                    posted_date = None
                    if date_el and date_el.get("datetime"):
                        try:
                            from datetime import datetime
                            posted_date = datetime.fromisoformat(date_el["datetime"])
                        except ValueError:
                            pass

                    jobs.append(JobData(
                        title=title,
                        source=self.SOURCE_NAME,
                        external_id=external_id,
                        company=company,
                        location="Nairobi, Kenya",
                        url=job_url,
                        posted_date=posted_date,
                    ))
                except Exception as e:
                    logger.debug(f"[CorporateStaffing] Card parse error: {e}")

            logger.info(f"[CorporateStaffing] Page {page_num}: {len(cards)} cards")

        logger.info(f"[CorporateStaffing] Total: {len(jobs)} jobs")
        return jobs
