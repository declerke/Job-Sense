import logging
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
]


@dataclass
class JobData:
    title: str
    source: str
    external_id: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: str = "KES"
    job_type: Optional[str] = None
    experience_level: Optional[str] = None
    remote: bool = False
    url: Optional[str] = None
    tags: Optional[str] = None
    requirements: Optional[str] = None
    posted_date: Optional[datetime] = None
    application_deadline: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


class BaseScraper(ABC):
    SOURCE_NAME: str = "unknown"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": random.choice(_USER_AGENTS),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",  # exclude brotli — requests can't decode it natively
            "Connection": "keep-alive",
        })

    def _rotate_ua(self):
        self.session.headers["User-Agent"] = random.choice(_USER_AGENTS)

    def fetch_page(self, url: str, params: dict = None, retries: int = 3) -> Optional[BeautifulSoup]:
        for attempt in range(retries):
            try:
                self._rotate_ua()
                resp = self.session.get(url, params=params, timeout=30)
                resp.raise_for_status()
                return BeautifulSoup(resp.text, "lxml")
            except requests.RequestException as e:
                logger.warning(f"[{self.SOURCE_NAME}] Attempt {attempt + 1}/{retries} failed for {url}: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
        return None

    def fetch_json(self, url: str, params: dict = None, headers: dict = None) -> Optional[dict]:
        try:
            self._rotate_ua()
            # Use JSON Accept header — overrides session's HTML Accept
            json_headers = {"Accept": "application/json"}
            if headers:
                json_headers.update(headers)
            resp = self.session.get(url, params=params, headers=json_headers, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            logger.error(f"[{self.SOURCE_NAME}] JSON fetch failed for {url}: {e}")
            return None

    @abstractmethod
    def scrape(self, max_pages: int = 5) -> list[JobData]:
        pass
