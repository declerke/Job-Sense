import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import jobs, cv_match

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
)

app = FastAPI(
    title="JobSense API",
    description="Kenya jobs intelligence — semantic search, CV matching, pipeline analytics",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router)
app.include_router(cv_match.router)


@app.get("/")
def root():
    return {
        "service": "JobSense API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": ["/api/jobs", "/api/stats", "/api/sources", "/api/cv-match", "/api/scrape-logs"],
    }


@app.get("/health")
def health():
    return {"status": "ok"}
