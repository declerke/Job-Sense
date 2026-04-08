import logging
import re

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, JobData

logger = logging.getLogger(__name__)

BASE_URL = "https://jobwebkenya.com"

class JobWebKenyaScraper(BaseScraper):
    SOURCE_NAME = "JobWebKenya"

    def scrape(self, max_pages: int = 5) -> list[JobData]:
        jobs: list[JobData] = []
        seen_urls: set[str] = set()

        for page_num in range(1, max_pages + 1):
            url = BASE_URL + "/" if page_num == 1 else f"{BASE_URL}/jobs/page/{page_num}/"
            soup = self.fetch_page(url)
            if not soup:
                break

            cards = soup.select("li.job, li.job-featured, li.job-alt")
            if not cards:
                logger.info(f"[JobWebKenya] No cards on page {page_num}, stopping.")
                break

            page_count = 0
            for card in cards:
                try:
                    job = self._parse_card(card, seen_urls)
                    if job:
                        jobs.append(job)
                        page_count += 1
                except Exception as e:
                    logger.debug(f"[JobWebKenya] Card parse error: {e}")

            logger.info(f"[JobWebKenya] Page {page_num}: {page_count} jobs from {len(cards)} cards")

        logger.info(f"[JobWebKenya] Total: {len(jobs)} jobs")
        return jobs

    def _parse_card(self, card, seen_urls: set) -> JobData | None:
        job_link = None
        for a in card.find_all("a", href=True):
            href = a["href"]
            if "jobwebkenya.com/jobs/" in href and "facebook" not in href and "twitter" not in href and "linkedin" not in href:
                job_link = a
                break

        if not job_link:
            return None

        href = job_link["href"]
        if href in seen_urls:
            return None
        seen_urls.add(href)

        title = job_link.get_text(strip=True)
        if not title or len(title) < 5:
            return None

        company = None
        at_match = re.search(r"\bat\b(.+)$", title, re.IGNORECASE)
        if at_match:
            company = at_match.group(1).strip()
        else:
            lista = card.select_one("div.lista")
            if lista:
                text = lista.get_text(" ", strip=True)
                first_sentence = text.split(".")[0].strip()
                if first_sentence and len(first_sentence) < 100:
                    company = first_sentence

        location = "Kenya"
        for div in card.find_all("div"):
            text = div.get_text(strip=True)
            if text.startswith("Location:"):
                location = text.replace("Location:", "").strip() or "Kenya"
                break

        jtype_el = card.select_one("span.jtype")
        job_type = jtype_el.get_text(strip=True).lower() if jtype_el else None
        
        job_type_map = {
            "full-time": "full-time", "full time": "full-time",
            "part-time": "part-time", "part time": "part-time",
            "contract": "contract", "internship": "internship",
            "freelance": "freelance", "temporary": "temporary",
        }
        job_type = job_type_map.get(job_type)

        external_id = href.rstrip("/").split("/")[-1]
        return JobData(
            title=title,
            source=self.SOURCE_NAME,
            external_id=external_id,
            company=company,
            location=location,
            job_type=job_type,
            url=href,
        )
