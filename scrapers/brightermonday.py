import logging

from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, JobData

logger = logging.getLogger(__name__)

BASE_URL = "https://www.brightermonday.co.ke"

# Broad queries covering all job categories, not just data roles
_QUERIES = [
    "jobs",           # general — returns mixed listings
    "engineer",
    "analyst",
    "officer",
    "manager",
    "developer",
    "accountant",
    "sales",
]


class BrighterMondayScraper(BaseScraper):
    SOURCE_NAME = "BrighterMonday"

    def scrape(self, max_pages: int = 5) -> list[JobData]:
        """
        BrighterMonday is an Alpine.js SPA — direct DOM selectors fail.
        Strategy:
          1. Playwright with network response interception (capture JSON API calls)
          2. HTML fallback using a[href*="/listings/"] link pattern
        Uses search queries rather than paginating /jobs/ directly.
        """
        from playwright.sync_api import sync_playwright

        jobs: list[JobData] = []
        seen_urls: set[str] = set()

        # Number of queries to run — scale with max_pages
        query_count = min(max_pages, len(_QUERIES))

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            )

            for query in _QUERIES[:query_count]:
                url = f"{BASE_URL}/jobs?q={query.replace(' ', '+')}"
                captured_json: list = []

                context = browser.new_context(
                    user_agent=self.session.headers["User-Agent"],
                    viewport={"width": 1280, "height": 800},
                )
                page = context.new_page()

                def handle_response(resp, _captured=captured_json):
                    try:
                        if resp.status != 200:
                            return
                        if "json" not in resp.headers.get("content-type", ""):
                            return
                        rurl = resp.url
                        if any(t in rurl for t in ["/jobs", "/listings", "/search", "/api", "/v1", "/v2"]):
                            _captured.append(resp.json())
                    except Exception:
                        pass

                page.on("response", handle_response)

                html_content = None
                try:
                    page.goto(url, wait_until="networkidle", timeout=30000)
                    page.wait_for_timeout(1000)
                    html_content = page.content()
                    logger.info(f"[BrighterMonday] '{query}': captured {len(captured_json)} JSON responses")
                except Exception as e:
                    logger.warning(f"[BrighterMonday] '{query}' load failed: {e}")
                finally:
                    context.close()

                # Primary: parse intercepted API JSON
                json_jobs = []
                for data in captured_json:
                    json_jobs.extend(self._parse_json(data, seen_urls))

                if json_jobs:
                    logger.info(f"[BrighterMonday] '{query}' JSON: {len(json_jobs)} jobs")
                    jobs.extend(json_jobs)
                elif html_content:
                    html_jobs = self._parse_html(html_content, seen_urls)
                    logger.info(f"[BrighterMonday] '{query}' HTML fallback: {len(html_jobs)} jobs")
                    jobs.extend(html_jobs)

            browser.close()

        logger.info(f"[BrighterMonday] Total: {len(jobs)} unique jobs")
        return jobs

    def _parse_json(self, data, seen_urls: set) -> list[JobData]:
        """Extract JobData objects from an intercepted JSON API response."""
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
            title = (item.get("title") or item.get("name") or
                     item.get("job_title") or item.get("position"))
            url = (item.get("url") or item.get("link") or
                   item.get("posting_url") or item.get("job_url"))
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
                company=(item.get("company") or item.get("employer") or
                         item.get("affiliation") or item.get("organisation")),
                location=(item.get("location") or item.get("location_name") or
                          item.get("city") or "Kenya"),
                description=(item.get("description") or item.get("snippet") or
                             item.get("summary")),
                url=url,
            ))
        return result

    def _parse_html(self, html: str, seen_urls: set) -> list[JobData]:
        """
        Fallback HTML parser using the known /listings/ URL pattern.
        BrighterMonday job detail pages always contain /listings/ in the path.
        """
        soup = BeautifulSoup(html, "lxml")
        result = []

        links = soup.select('a[href*="/listings/"]')
        for link in links:
            href = link.get("href", "")
            if not href:
                continue
            url = href if href.startswith("http") else f"{BASE_URL}{href}"
            if url in seen_urls:
                continue
            seen_urls.add(url)

            title = link.get_text(strip=True)
            if not title or len(title) < 4:
                continue

            # Walk up DOM to find card container with enough context
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
                co_el = card.select_one('a[href*="/company/"]')
                if co_el:
                    company = co_el.get_text(strip=True)
                card_text = card.get_text(" ", strip=True).lower()
                for loc in ["nairobi", "mombasa", "kisumu", "eldoret", "nakuru", "remote"]:
                    if loc in card_text:
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
