import os
import sys
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

# Ensure project root is on path
PROJECT_ROOT = "/opt/airflow/jobsense"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

default_args = {
    "owner": "jobsense",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

# ── Task callables ─────────────────────────────────────────────────────────────

def scrape_source(source_name: str, **kwargs):
    from scrapers.runner import run_scraper
    result = run_scraper(source_name, max_pages=5)
    if result["status"] == "failed":
        raise RuntimeError(f"Scraper {source_name} failed: {result.get('error')}")
    kwargs["ti"].xcom_push(key=f"{source_name}_result", value=result)
    return result


def embed_jobs(**kwargs):
    import psycopg2
    from config.settings import settings
    from pipeline.embedder import embed_unprocessed_jobs

    conn = psycopg2.connect(
        host=settings.POSTGRES_HOST, port=settings.POSTGRES_PORT,
        dbname=settings.POSTGRES_DB, user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
    )
    try:
        count = embed_unprocessed_jobs(conn)
        kwargs["ti"].xcom_push(key="embedded_count", value=count)
        print(f"[Embed] Embedded {count} new jobs")
        return count
    finally:
        conn.close()


def log_summary(**kwargs):
    ti = kwargs["ti"]
    sources = [
        "BrighterMonday", "MyJobMag", "Fuzu", "Adzuna",
        "RemoteOK", "CareerPointKenya", "JobWebKenya", "CorporateStaffing",
    ]
    total_found = total_new = 0
    print("\n" + "=" * 55)
    print("  JOBSENSE PIPELINE SUMMARY")
    print("=" * 55)
    for src in sources:
        result = ti.xcom_pull(key=f"{src}_result", task_ids=f"scrape_{src.lower().replace(' ', '_')}")
        if result:
            found = result.get("jobs_found", 0)
            new   = result.get("jobs_new", 0)
            total_found += found
            total_new   += new
            status = "✓" if result.get("status") == "success" else "✗"
            print(f"  {status} {src:<22} found={found:>4}  new={new:>4}")
    print("-" * 55)
    print(f"    TOTAL                    found={total_found:>4}  new={total_new:>4}")
    embedded = ti.xcom_pull(key="embedded_count", task_ids="embed_jobs") or 0
    print(f"    Embeddings generated: {embedded}")
    print("=" * 55)


# ── DAG ───────────────────────────────────────────────────────────────────────

with DAG(
    dag_id="jobsense_pipeline",
    default_args=default_args,
    description="Scrape → dbt → embed daily pipeline",
    schedule="0 4 * * *",       # 04:00 UTC = 07:00 EAT
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["jobsense", "pipeline", "scraping", "embedding"],
    max_active_runs=1,
) as dag:

    # ── Scrape tasks (fan-out, run in parallel) ───────────────────────────────
    SOURCES = [
        "BrighterMonday", "MyJobMag", "Fuzu", "Adzuna",
        "RemoteOK", "CareerPointKenya", "JobWebKenya", "CorporateStaffing",
    ]

    scrape_tasks = []
    for source in SOURCES:
        task_id = f"scrape_{source.lower().replace(' ', '_')}"
        t = PythonOperator(
            task_id=task_id,
            python_callable=scrape_source,
            op_kwargs={"source_name": source},
        )
        scrape_tasks.append(t)

    # ── dbt run ───────────────────────────────────────────────────────────────
    DBT_BIN = "/home/airflow/.local/bin/dbt"
    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=(
            f"cd {PROJECT_ROOT}/dbt && "
            f"{DBT_BIN} deps --profiles-dir . && "
            f"{DBT_BIN} run --profiles-dir . --target dev"
        ),
        env={
            "POSTGRES_HOST":     os.getenv("POSTGRES_HOST", "postgres"),
            "POSTGRES_PORT":     os.getenv("POSTGRES_PORT", "5432"),
            "POSTGRES_DB":       os.getenv("POSTGRES_DB", "jobsense"),
            "POSTGRES_USER":     os.getenv("POSTGRES_USER", "jobsense"),
            "POSTGRES_PASSWORD": os.getenv("POSTGRES_PASSWORD", "jobsense_secret"),
            "PATH": "/home/airflow/.local/bin:/usr/local/bin:/usr/bin:/bin",
        },
    )

    # ── dbt test ──────────────────────────────────────────────────────────────
    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=(
            f"cd {PROJECT_ROOT}/dbt && "
            f"{DBT_BIN} test --profiles-dir . --target dev"
        ),
        env={
            "POSTGRES_HOST":     os.getenv("POSTGRES_HOST", "postgres"),
            "POSTGRES_PORT":     os.getenv("POSTGRES_PORT", "5432"),
            "POSTGRES_DB":       os.getenv("POSTGRES_DB", "jobsense"),
            "POSTGRES_USER":     os.getenv("POSTGRES_USER", "jobsense"),
            "POSTGRES_PASSWORD": os.getenv("POSTGRES_PASSWORD", "jobsense_secret"),
            "PATH": "/home/airflow/.local/bin:/usr/local/bin:/usr/bin:/bin",
        },
    )

    # ── Embed ─────────────────────────────────────────────────────────────────
    embed_task = PythonOperator(
        task_id="embed_jobs",
        python_callable=embed_jobs,
    )

    # ── Summary ───────────────────────────────────────────────────────────────
    summary_task = PythonOperator(
        task_id="log_summary",
        python_callable=log_summary,
        provide_context=True,
    )

    # ── Dependencies: all scrapers → dbt run → dbt test → embed → summary ────
    scrape_tasks >> dbt_run >> dbt_test >> embed_task >> summary_task
