import io
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def _make_pdf_bytes(text: str = "Data Engineer with Python and SQL experience.") -> bytes:
    try:
        from reportlab.pdfgen import canvas
        buf = io.BytesIO()
        c = canvas.Canvas(buf)
        c.drawString(100, 750, text)
        c.save()
        return buf.getvalue()
    except ImportError:
        return b"%PDF-1.4 fake pdf content for testing"


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_root():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "JobSense" in resp.json()["service"]


def test_cv_match_rejects_non_pdf():
    resp = client.post(
        "/api/cv-match",
        files={"cv_file": ("resume.docx", b"fake content", "application/octet-stream")},
        data={"top_k": 5},
    )
    assert resp.status_code == 400
    assert "PDF" in resp.json()["detail"]


def test_cv_match_rejects_oversized_file():
    big_file = b"x" * (6 * 1024 * 1024)
    resp = client.post(
        "/api/cv-match",
        files={"cv_file": ("cv.pdf", big_file, "application/pdf")},
        data={"top_k": 5},
    )
    assert resp.status_code == 400
    assert "5 MB" in resp.json()["detail"]


def test_cv_match_returns_ranked_matches():
    mock_jobs = [
        {
            "id": 1, "title": "Data Engineer", "company": "Safaricom",
            "location": "Nairobi", "job_type": "full-time", "experience_level": "mid",
            "remote": False, "url": "https://example.com/1", "source": "BrighterMonday",
            "tags": "python,sql,airflow", "description": "Build ETL pipelines.",
            "posted_date": None, "scraped_at": None, "similarity": 0.91,
        },
        {
            "id": 2, "title": "Analytics Engineer", "company": "Twiga Foods",
            "location": "Nairobi", "job_type": "full-time", "experience_level": "mid",
            "remote": False, "url": "https://example.com/2", "source": "MyJobMag",
            "tags": "python,dbt,sql", "description": "Build dbt models.",
            "posted_date": None, "scraped_at": None, "similarity": 0.87,
        },
    ]
    mock_analysis = [
        {"job_id": 1, "match_score": 91, "strengths": ["Python", "SQL"], "gaps": ["Spark"], "recommendation": "Strong match."},
        {"job_id": 2, "match_score": 82, "strengths": ["dbt", "SQL"], "gaps": ["Kafka"], "recommendation": "Good fit."},
    ]

    with patch("api.routers.cv_match.extract_pdf_text", return_value="Senior Python data engineer with Airflow and dbt."), \
         patch("api.routers.cv_match.embed_cv_text",    return_value=[0.1] * 384), \
         patch("api.routers.cv_match.search_similar_jobs", return_value=mock_jobs), \
         patch("api.routers.cv_match.call_claude_match", return_value=mock_analysis), \
         patch("psycopg2.connect"):

        pdf_bytes = _make_pdf_bytes()
        resp = client.post(
            "/api/cv-match",
            files={"cv_file": ("cv.pdf", pdf_bytes, "application/pdf")},
            data={"top_k": 10},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert "matches" in body
    assert len(body["matches"]) == 2
    scores = [m["match_score"] for m in body["matches"]]
    assert scores == sorted(scores, reverse=True)


def test_claude_fallback_without_api_key():
    from api.routers.cv_match import call_claude_match
    jobs = [{"id": 1, "similarity": 0.85}, {"id": 2, "similarity": 0.60}]
    with patch("api.routers.cv_match.settings") as mock_settings:
        mock_settings.ANTHROPIC_API_KEY = ""
        result = call_claude_match("Python engineer CV text", jobs)

    assert len(result) == 2
    assert result[0]["job_id"] == 1
    assert result[0]["match_score"] == 85
