import json
import logging
from typing import Optional

import pdfplumber
import anthropic
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from api.database import get_db
from api.schemas import CVMatchResponse, JobMatch, JobResponse
from config.settings import settings
from pipeline.embedder import embed_cv_text, search_similar_jobs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["cv-match"])

CLAUDE_MODEL = "claude-haiku-4-5-20251001"

MATCH_PROMPT = """You are a senior technical recruiter. A candidate has submitted their CV and I have retrieved the {n} most semantically similar job postings from our database.

Candidate CV (excerpt):
\"\"\"
{cv_text}
\"\"\"

Job Postings:
{jobs_text}

For each job posting, provide a JSON analysis with EXACTLY this structure:
{{
  "job_id": <integer>,
  "match_score": <integer 0-100>,
  "strengths": [<up to 3 short strings of matching skills/experience>],
  "gaps": [<up to 3 short strings of missing skills>],
  "recommendation": "<one sentence max>"
}}

Return a JSON array of {n} objects, one per job. No other text.
"""


def extract_pdf_text(file_bytes: bytes) -> str:
    import io
    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages[:5]:  # cap at first 5 pages
            text = page.extract_text()
            if text:
                text_parts.append(text)
    return "\n".join(text_parts).strip()


def format_jobs_for_prompt(jobs: list[dict]) -> str:
    lines = []
    for i, job in enumerate(jobs, 1):
        tags = job.get("tags") or "not specified"
        salary = ""
        if job.get("salary_min") or job.get("salary_max"):
            lo = job.get("salary_min", "?")
            hi = job.get("salary_max", "?")
            salary = f" | Salary: {lo}–{hi} {job.get('salary_currency', 'KES')}"
        lines.append(
            f"[{job['id']}] {job['title']} @ {job.get('company', 'Unknown')} "
            f"| {job.get('location', 'Kenya')}{salary}\n"
            f"     Tags: {tags}\n"
            f"     {(job.get('description') or '')[:200]}"
        )
    return "\n\n".join(lines)


def call_claude_match(cv_text: str, jobs: list[dict]) -> list[dict]:
    if not settings.ANTHROPIC_API_KEY:
        # Fallback: return similarity-based scores without LLM analysis
        logger.warning("[CVMatch] No Anthropic API key — using similarity scores only.")
        return [
            {
                "job_id": job["id"],
                "match_score": int(job.get("similarity", 0) * 100),
                "strengths": [],
                "gaps": [],
                "recommendation": "Set ANTHROPIC_API_KEY for detailed analysis.",
            }
            for job in jobs
        ]

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    prompt = MATCH_PROMPT.format(
        n=len(jobs),
        cv_text=cv_text[:1500],
        jobs_text=format_jobs_for_prompt(jobs),
    )

    try:
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except (json.JSONDecodeError, anthropic.APIError) as e:
        logger.error(f"[CVMatch] Claude call failed: {e}")
        return [
            {
                "job_id": job["id"],
                "match_score": int(job.get("similarity", 0) * 100),
                "strengths": [],
                "gaps": [],
                "recommendation": "Analysis unavailable — check API key.",
            }
            for job in jobs
        ]


@router.post("/cv-match", response_model=CVMatchResponse)
async def cv_match(
    cv_file: UploadFile = File(..., description="PDF CV/resume"),
    top_k: int = Form(10, ge=1, le=20),
    db: Session = Depends(get_db),
):
    # 1. Validate file type
    if not cv_file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    file_bytes = await cv_file.read()
    if len(file_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="CV file must be under 5 MB.")

    # 2. Extract text
    cv_text = extract_pdf_text(file_bytes)
    if not cv_text or len(cv_text) < 50:
        raise HTTPException(status_code=422, detail="Could not extract text from PDF. Ensure it is not a scanned image.")

    # 3. Embed CV
    cv_vector = embed_cv_text(cv_text)

    # 4. pgvector similarity search — uses raw psycopg2 for vector ops
    import psycopg2
    conn = psycopg2.connect(
        host=settings.POSTGRES_HOST, port=settings.POSTGRES_PORT,
        dbname=settings.POSTGRES_DB, user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
    )
    try:
        similar_jobs = search_similar_jobs(conn, cv_vector, top_k=top_k)
    finally:
        conn.close()

    if not similar_jobs:
        raise HTTPException(
            status_code=503,
            detail="No embedded jobs found. Run the pipeline first to populate embeddings.",
        )

    # 5. Claude match analysis
    analysis_list = call_claude_match(cv_text, similar_jobs)

    # 6. Merge similarity scores with LLM analysis
    analysis_map = {a["job_id"]: a for a in analysis_list}
    matches = []
    for job in similar_jobs:
        analysis = analysis_map.get(job["id"], {})
        matches.append(JobMatch(
            job=JobResponse(
                id=job["id"],
                title=job["title"],
                company=job.get("company"),
                location=job.get("location"),
                description=job.get("description"),
                job_type=job.get("job_type"),
                experience_level=job.get("experience_level"),
                remote=job.get("remote", False),
                url=job.get("url"),
                source=job.get("source", ""),
                tags=job.get("tags"),
                posted_date=job.get("posted_date"),
                scraped_at=job.get("scraped_at"),
            ),
            similarity_score=round(float(job.get("similarity", 0)), 4),
            match_score=analysis.get("match_score", int(job.get("similarity", 0) * 100)),
            strengths=analysis.get("strengths", []),
            gaps=analysis.get("gaps", []),
            recommendation=analysis.get("recommendation", ""),
        ))

    # Sort by match_score descending
    matches.sort(key=lambda m: m.match_score, reverse=True)

    return CVMatchResponse(
        cv_summary=cv_text[:300],
        matches=matches,
        model_used=CLAUDE_MODEL if settings.ANTHROPIC_API_KEY else "similarity-only",
    )
