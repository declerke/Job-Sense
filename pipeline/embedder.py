import logging
import os
from typing import Optional

import psycopg2
import psycopg2.extras
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer

from config.settings import settings

logger = logging.getLogger(__name__)

_model: Optional[SentenceTransformer] = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info(f"[Embedder] Loading model: {settings.EMBEDDING_MODEL}")
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _model


def build_embedding_text(row: dict) -> str:
    parts = [
        row.get("title") or "",
        row.get("company") or "",
        row.get("location") or "",
        row.get("job_type") or "",
        row.get("experience_level") or "",
        row.get("tags") or "",
        (row.get("description") or "")[:500],
    ]
    return " ".join(p for p in parts if p).strip()


def embed_unprocessed_jobs(conn, batch_size: int = 64) -> int:
    register_vector(conn)
    model = get_model()

    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("""
            SELECT id, title, company, location, job_type, experience_level, tags, description
            FROM jobs
            WHERE is_active = TRUE AND embedding IS NULL
            ORDER BY scraped_at DESC
        """)
        rows = cur.fetchall()

    if not rows:
        logger.info("[Embedder] No unembedded jobs found.")
        return 0

    logger.info(f"[Embedder] Embedding {len(rows)} jobs in batches of {batch_size}...")
    total_embedded = 0

    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        texts = [build_embedding_text(dict(row)) for row in batch]
        ids = [row["id"] for row in batch]

        vectors = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)

        with conn.cursor() as cur:
            for job_id, vector in zip(ids, vectors):
                cur.execute(
                    "UPDATE jobs SET embedding = %s WHERE id = %s",
                    (vector.tolist(), job_id),
                )
        conn.commit()
        total_embedded += len(batch)
        logger.info(f"[Embedder] Embedded {total_embedded}/{len(rows)} jobs")

    _ensure_ivfflat_index(conn)

    return total_embedded


def _ensure_ivfflat_index(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM jobs WHERE embedding IS NOT NULL")
        count = cur.fetchone()[0]

    if count < 100:
        logger.info(f"[Embedder] Only {count} embeddings — skipping IVFFlat index build (need ≥ 100)")
        return

    with conn.cursor() as cur:
        cur.execute("""
            SELECT 1 FROM pg_indexes
            WHERE tablename = 'jobs' AND indexname = 'idx_jobs_embedding'
        """)
        exists = cur.fetchone()

    if not exists:
        logger.info("[Embedder] Building IVFFlat index on jobs.embedding...")
        with conn.cursor() as cur:
            cur.execute("""
                CREATE INDEX idx_jobs_embedding
                ON jobs USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """)
        conn.commit()
        logger.info("[Embedder] IVFFlat index created.")


def embed_cv_text(cv_text: str) -> list[float]:
    model = get_model()
    vector = model.encode(cv_text[:2000], normalize_embeddings=True)
    return vector.tolist()


def search_similar_jobs(conn, cv_vector: list[float], top_k: int = 10) -> list[dict]:
    register_vector(conn)

    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("""
            SELECT
                id, title, company, location, job_type, experience_level,
                remote, url, source, tags, description, posted_date,
                1 - (embedding <=> %s::vector) AS similarity
            FROM jobs
            WHERE is_active = TRUE AND embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, (cv_vector, cv_vector, top_k))
        rows = cur.fetchall()

    return [dict(row) for row in rows]
