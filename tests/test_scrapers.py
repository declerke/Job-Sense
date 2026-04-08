import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from scrapers.base_scraper import JobData


def _assert_valid_jobs(jobs: list, source_name: str, min_count: int = 1):
    assert isinstance(jobs, list), f"{source_name}: expected list"
    assert len(jobs) >= min_count, f"{source_name}: expected ≥{min_count} jobs, got {len(jobs)}"
    for job in jobs[:3]:
        assert isinstance(job, JobData), f"{source_name}: item is not JobData"
        assert job.title and len(job.title) > 3, f"{source_name}: job title too short: {job.title!r}"
        assert job.source == source_name, f"Source mismatch: {job.source!r} != {source_name!r}"


@pytest.mark.integration
def test_adzuna_scraper():
    from scrapers.adzuna import AdzunaScraper
    jobs = AdzunaScraper().scrape(max_pages=1)
    assert isinstance(jobs, list)


@pytest.mark.integration
def test_remoteok_scraper():
    from scrapers.remoteok import RemoteOKScraper
    jobs = RemoteOKScraper().scrape(max_pages=1)
    _assert_valid_jobs(jobs, "RemoteOK", min_count=5)
    assert all(j.remote for j in jobs), "All RemoteOK jobs should be remote"


@pytest.mark.integration
def test_myjobmag_scraper():
    from scrapers.myjobmag import MyJobMagScraper
    jobs = MyJobMagScraper().scrape(max_pages=1)
    _assert_valid_jobs(jobs, "MyJobMag", min_count=5)


@pytest.mark.integration
def test_careerpointkenya_scraper():
    from scrapers.careerpointkenya import CareerPointKenyaScraper
    jobs = CareerPointKenyaScraper().scrape(max_pages=1)
    _assert_valid_jobs(jobs, "CareerPointKenya", min_count=1)


@pytest.mark.integration
def test_jobwebkenya_scraper():
    from scrapers.jobwebkenya import JobWebKenyaScraper
    jobs = JobWebKenyaScraper().scrape(max_pages=1)
    assert isinstance(jobs, list)


@pytest.mark.integration
def test_corporatestaffing_scraper():
    from scrapers.corporatestaffing import CorporateStaffingScraper
    jobs = CorporateStaffingScraper().scrape(max_pages=1)
    assert isinstance(jobs, list)


def test_jobdata_to_dict_includes_all_fields():
    job = JobData(
        title="Data Engineer",
        source="BrighterMonday",
        company="Safaricom",
        location="Nairobi",
        remote=False,
        tags="python,sql",
    )
    d = job.to_dict()
    assert d["title"] == "Data Engineer"
    assert d["source"] == "BrighterMonday"
    assert d["remote"] is False
    assert "external_id" in d

def test_jobdata_defaults():
    job = JobData(title="Analyst", source="test")
    assert job.remote is False
    assert job.salary_currency == "KES"
    assert job.company is None
