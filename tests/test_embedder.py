import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from pipeline.embedder import build_embedding_text, embed_cv_text, get_model


def test_build_embedding_text_combines_fields():
    row = {
        "title": "Data Engineer",
        "company": "Safaricom",
        "location": "Nairobi",
        "job_type": "full-time",
        "tags": "python,sql,airflow",
        "description": "Build pipelines.",
    }
    text = build_embedding_text(row)
    assert "Data Engineer" in text
    assert "Safaricom" in text
    assert "python" in text

def test_build_embedding_text_handles_none_fields():
    row = {"title": "Analyst", "company": None, "tags": None, "description": None}
    text = build_embedding_text(row)
    assert "Analyst" in text
    assert text.strip() != ""


def test_embed_cv_text_returns_correct_shape():
    cv_text = "Experienced data engineer with Python, SQL, Airflow, and dbt skills."
    vector = embed_cv_text(cv_text)
    assert isinstance(vector, list)
    assert len(vector) == 384
    assert all(isinstance(v, float) for v in vector[:5])

def test_embed_cv_text_normalised():
    import math
    vector = embed_cv_text("Data Engineering portfolio project.")
    magnitude = math.sqrt(sum(v ** 2 for v in vector))
    assert abs(magnitude - 1.0) < 0.01


def test_similar_texts_have_higher_cosine_similarity():
    import numpy as np
    model = get_model()

    cv = "Senior Python data engineer experienced with Airflow, dbt, and Kafka."
    similar_job = "Data Engineer — Python, Airflow, dbt, PostgreSQL"
    unrelated_job = "Marketing Manager — brand strategy and social media campaigns"

    cv_vec     = model.encode(cv,           normalize_embeddings=True)
    sim_vec    = model.encode(similar_job,  normalize_embeddings=True)
    unrela_vec = model.encode(unrelated_job, normalize_embeddings=True)

    score_sim   = float(np.dot(cv_vec, sim_vec))
    score_unrela = float(np.dot(cv_vec, unrela_vec))

    assert score_sim > score_unrela, (
        f"Expected similar job ({score_sim:.3f}) to outscore unrelated job ({score_unrela:.3f})"
    )


@pytest.mark.integration
def test_embed_and_retrieve(tmp_db_conn):
    from pipeline.embedder import embed_unprocessed_jobs, search_similar_jobs

    with tmp_db_conn.cursor() as cur:
        cur.execute("""
            INSERT INTO jobs (title, source, description, is_active)
            VALUES ('Python Data Engineer', 'TestSource', 'Build ETL pipelines with Python and SQL.', TRUE)
            RETURNING id
        """)
        job_id = cur.fetchone()[0]
    tmp_db_conn.commit()

    count = embed_unprocessed_jobs(tmp_db_conn)
    assert count >= 1

    cv_vector = embed_cv_text("Python engineer with SQL and ETL experience.")
    results = search_similar_jobs(tmp_db_conn, cv_vector, top_k=5)
    job_ids = [r["id"] for r in results]
    assert job_id in job_ids
