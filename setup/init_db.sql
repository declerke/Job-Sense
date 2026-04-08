-- JobSense Database Schema
-- Requires pgvector extension (provided by pgvector/pgvector:pg15 image)

CREATE EXTENSION IF NOT EXISTS vector;

-- ─────────────────────────────────────────────
-- Core jobs table
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS jobs (
    id                   SERIAL PRIMARY KEY,
    external_id          VARCHAR(500),
    title                VARCHAR(500) NOT NULL,
    company              VARCHAR(300),
    location             VARCHAR(300),
    description          TEXT,
    salary_min           NUMERIC(12, 2),
    salary_max           NUMERIC(12, 2),
    salary_currency      VARCHAR(10) DEFAULT 'KES',
    job_type             VARCHAR(50),           -- full-time, part-time, contract, internship, freelance
    experience_level     VARCHAR(50),           -- entry, mid, senior, executive
    remote               BOOLEAN DEFAULT FALSE,
    url                  VARCHAR(1000),
    source               VARCHAR(100) NOT NULL,
    tags                 TEXT,                  -- comma-separated skill tags
    requirements         TEXT,
    posted_date          TIMESTAMP,
    application_deadline TIMESTAMP,
    scraped_at           TIMESTAMP DEFAULT NOW(),
    is_active            BOOLEAN DEFAULT TRUE,
    embedding            vector(384),           -- sentence-transformers/all-MiniLM-L6-v2
    CONSTRAINT uq_jobs_source_external UNIQUE (source, external_id)
);

-- Standard indexes
CREATE INDEX IF NOT EXISTS idx_jobs_source        ON jobs(source);
CREATE INDEX IF NOT EXISTS idx_jobs_is_active     ON jobs(is_active, scraped_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_job_type      ON jobs(job_type);
CREATE INDEX IF NOT EXISTS idx_jobs_experience    ON jobs(experience_level);
CREATE INDEX IF NOT EXISTS idx_jobs_remote        ON jobs(remote);
CREATE INDEX IF NOT EXISTS idx_jobs_scraped_at    ON jobs(scraped_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_posted_date   ON jobs(posted_date DESC);

-- Full-text search index
CREATE INDEX IF NOT EXISTS idx_jobs_fts ON jobs USING GIN (
    to_tsvector('english',
        COALESCE(title, '') || ' ' ||
        COALESCE(company, '') || ' ' ||
        COALESCE(description, '') || ' ' ||
        COALESCE(tags, '')
    )
);

-- pgvector IVFFlat index (built after sufficient rows are inserted)
-- NOTE: requires ≥ 100 rows. The application creates this after first pipeline run.
-- CREATE INDEX IF NOT EXISTS idx_jobs_embedding ON jobs
--     USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ─────────────────────────────────────────────
-- Scrape audit log
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS scrape_logs (
    id               SERIAL PRIMARY KEY,
    source           VARCHAR(100) NOT NULL,
    status           VARCHAR(20) CHECK (status IN ('running', 'success', 'partial', 'failed')),
    jobs_found       INTEGER DEFAULT 0,
    jobs_new         INTEGER DEFAULT 0,
    jobs_updated     INTEGER DEFAULT 0,
    jobs_embedded    INTEGER DEFAULT 0,
    error_message    TEXT,
    started_at       TIMESTAMP DEFAULT NOW(),
    finished_at      TIMESTAMP,
    duration_seconds NUMERIC(10, 2)
);

CREATE INDEX IF NOT EXISTS idx_scrape_logs_source ON scrape_logs(source, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_scrape_logs_status ON scrape_logs(status, started_at DESC);

-- ─────────────────────────────────────────────
-- Keyword priority reference table
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS keyword_priorities (
    keyword  VARCHAR(100) PRIMARY KEY,
    priority INTEGER DEFAULT 1 CHECK (priority BETWEEN 1 AND 5),
    category VARCHAR(50)
);

INSERT INTO keyword_priorities (keyword, priority, category) VALUES
    ('Python',          5, 'Programming'),
    ('SQL',             5, 'Database'),
    ('dbt',             5, 'Transformation'),
    ('Apache Airflow',  5, 'Orchestration'),
    ('Kafka',           5, 'Streaming'),
    ('Spark',           5, 'Big Data'),
    ('PostgreSQL',      5, 'Database'),
    ('BigQuery',        5, 'Cloud DW'),
    ('AWS',             5, 'Cloud'),
    ('GCP',             5, 'Cloud'),
    ('Azure',           5, 'Cloud'),
    ('Docker',          4, 'DevOps'),
    ('Kubernetes',      4, 'DevOps'),
    ('Terraform',       4, 'IaC'),
    ('FastAPI',         4, 'Framework'),
    ('ETL',             5, 'Data Engineering'),
    ('Data Pipeline',   5, 'Data Engineering'),
    ('Machine Learning',4, 'AI/ML'),
    ('Power BI',        3, 'Visualization'),
    ('Tableau',         3, 'Visualization'),
    ('Pandas',          4, 'Data Processing'),
    ('Snowflake',       4, 'Cloud DW'),
    ('Redis',           3, 'Database'),
    ('MongoDB',         3, 'Database'),
    ('Git',             3, 'Version Control'),
    ('CI/CD',           4, 'DevOps'),
    ('React',           3, 'Frontend'),
    ('Java',            3, 'Programming'),
    ('Scala',           4, 'Big Data')
ON CONFLICT (keyword) DO NOTHING;

-- ─────────────────────────────────────────────
-- Useful views
-- ─────────────────────────────────────────────
CREATE OR REPLACE VIEW v_active_jobs AS
SELECT
    id, title, company, location, salary_min, salary_max, salary_currency,
    job_type, experience_level, remote, url, source, tags,
    posted_date, scraped_at,
    embedding IS NOT NULL AS has_embedding
FROM jobs
WHERE is_active = TRUE
ORDER BY scraped_at DESC;

CREATE OR REPLACE VIEW v_source_stats AS
SELECT
    source,
    COUNT(*)                                            AS total_jobs,
    COUNT(*) FILTER (WHERE is_active = TRUE)            AS active_jobs,
    COUNT(*) FILTER (WHERE embedding IS NOT NULL)       AS embedded_jobs,
    MAX(scraped_at)                                     AS last_scraped,
    MIN(scraped_at)                                     AS first_scraped
FROM jobs
GROUP BY source
ORDER BY total_jobs DESC;

CREATE OR REPLACE VIEW v_trending_skills AS
SELECT
    TRIM(skill)           AS skill,
    COUNT(*)              AS frequency,
    COUNT(DISTINCT source) AS source_count
FROM jobs,
     UNNEST(STRING_TO_ARRAY(tags, ',')) AS skill
WHERE is_active = TRUE
  AND scraped_at > NOW() - INTERVAL '30 days'
  AND tags IS NOT NULL
GROUP BY TRIM(skill)
ORDER BY frequency DESC;

-- Auto-update trigger
CREATE OR REPLACE FUNCTION set_duration()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.finished_at IS NOT NULL AND NEW.started_at IS NOT NULL THEN
        NEW.duration_seconds := EXTRACT(EPOCH FROM (NEW.finished_at - NEW.started_at));
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_scrape_logs_duration
BEFORE UPDATE ON scrape_logs
FOR EACH ROW EXECUTE FUNCTION set_duration();

DO $$ BEGIN
    RAISE NOTICE 'JobSense schema initialised successfully.';
END $$;
