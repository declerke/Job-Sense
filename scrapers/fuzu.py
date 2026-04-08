import logging
import time

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, JobData

logger = logging.getLogger(__name__)

BASE_URL = "https://fuzu.com"
JOBS_URL = f"{BASE_URL}/kenya/jobs"

# Fuzu is Cloudflare-protected — requests always returns 403.
# Playwright passes the JS challenge and gets full page HTML.
# Job posting URLs use /kenya/jobs/<slug> (plural).
# /kenya/job/<location> (singular) is for location/category filters — ignore.


class FuzuScraper(BaseScraper):
    SOURCE_NAME = "Fuzu"

    def scrape(self, max_pages: int = 5) -> list[JobData]:
        return self._scrape_playwright(max_pages)

    def _scrape_playwright(self, max_pages: int) -> list[JobData]:
        from playwright.sync_api import sync_playwright

        jobs: list[JobData] = []
        seen_urls: set[str] = set()

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            context = browser.new_context(
                user_agent=self.session.headers["User-Agent"],
                viewport={"width": 1280, "height": 800},
            )

            for page_num in range(1, max_pages + 1):
                url = f"{JOBS_URL}?page={page_num}"
                captured_json: list = []
                page = context.new_page()

                def handle_response(resp, _captured=captured_json):
                    try:
                        if resp.status != 200:
                            return
                        if "json" not in resp.headers.get("content-type", ""):
                            return
                        rurl = resp.url
                        if any(t in rurl for t in ["/jobs", "/api", "/search", "/v1", "/v2"]):
                            _captured.append(resp.json())
                    except Exception:
                        pass

                page.on("response", handle_response)

                html_content = None
                try:
                    page.goto(url, wait_until="networkidle", timeout=30000)
                    page.wait_for_timeout(1500)
                    html_content = page.content()
                    logger.info(f"[Fuzu] Page {page_num}: {len(captured_json)} JSON responses captured")
                except Exception as e:
                    logger.warning(f"[Fuzu] Page {page_num} failed: {e}")
                    page.close()
                    break
                finally:
                    try:
                        page.close()
                    except Exception:
                        pass

                # Primary: intercepted JSON API
                json_jobs = []
                for data in captured_json:
                    json_jobs.extend(self._parse_json(data, seen_urls))

                if json_jobs:
                    logger.info(f"[Fuzu] Page {page_num} JSON: {len(json_jobs)} jobs")
                    jobs.extend(json_jobs)
                elif html_content:
                    html_jobs = self._parse_html(html_content, seen_urls)
                    logger.info(f"[Fuzu] Page {page_num} HTML: {len(html_jobs)} jobs")
                    jobs.extend(html_jobs)
                    if not html_jobs:
                        break  # no more pages
                else:
                    break

            context.close()
            browser.close()

        logger.info(f"[Fuzu] Total: {len(jobs)} jobs")
        return jobs

    def _parse_html(self, html: str, seen_urls: set) -> list[JobData]:
        """
        Parse Fuzu HTML. Job postings use /kenya/jobs/<slug> links (with 's').
        /kenya/job/<location> (no 's') links are category/location filters — skip them.
        """
        soup = BeautifulSoup(html, "lxml")
        result = []

        job_links = soup.select('a[href*="/kenya/jobs/"]')

        for link in job_links:
            href = link.get("href", "")
            if not href:
                continue
            url = href if href.startswith("http") else f"{BASE_URL}{href}"
            if url in seen_urls:
                continue
            seen_urls.add(url)

            # Title: try heading inside link, fall back to link text
            title_el = link.select_one("h2, h3, [class*='title'], [class*='Title']")
            title = (title_el or link).get_text(strip=True)
            if not title or len(title) < 4:
                continue

            # Walk up to card container for company/location context
            card = link.parent
            for _ in range(6):
                if card is None:
                    break
                if card.name in ("article", "div", "li", "section"):
                    if len(card.get_text(" ", strip=True)) > len(title) + 10:
                        break
                card = card.parent

            company = None
            location = "Kenya"
            if card:
                card_text = card.get_text(" ", strip=True)
                co_el = card.select_one('a[href*="/company/"], a[href*="/employer/"]')
                if co_el:
                    company = co_el.get_text(strip=True)
                lower = card_text.lower()
                for loc in ["nairobi", "mombasa", "kisumu", "eldoret", "nakuru", "remote"]:
                    if loc in lower:
                        location = loc.title()
                        break

            external_id = href.rstrip("/").split("/")[-1]
            result.append(JobData(
                title=title,
                source=self.SOURCE_NAME,
                external_id=external_id,
                company=company,
                location=location,
                url=url,
            ))

        return result

    def _parse_json(self, data, seen_urls: set) -> list[JobData]:
        """Parse job data from intercepted JSON API responses."""
        items: list = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            for key in ("jobs", "results", "data", "listings", "items"):
                if data.get(key):
                    items = data[key]
                    break

        result = []
        for item in items:
            if not isinstance(item, dict):
                continue
            title = item.get("title") or item.get("name") or item.get("job_title")
            url = item.get("url") or item.get("link") or item.get("posting_url")
            if not title or not url:
                continue
            if not url.startswith("http"):
                url = f"{BASE_URL}{url}"
            if url in seen_urls:
                continue
            seen_urls.add(url)

            external_id = url.rstrip("/").split("/")[-1]
            result.append(JobData(
                title=title.strip(),
                source=self.SOURCE_NAME,
                external_id=external_id,
                company=item.get("company") or item.get("employer"),
                location=item.get("location") or "Kenya",
                description=item.get("description") or item.get("snippet"),
                url=url,
            ))

        return result
