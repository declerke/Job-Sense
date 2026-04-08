import os

import requests
import streamlit as st

st.set_page_config(
    page_title="JobSense — Kenya Jobs Intelligence",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  #MainMenu, footer, header {visibility: hidden;}

  .stApp { background-color: #0A0E1A; }

  [data-testid="stSidebar"] {
    background-color: #0D1117;
    border-right: 1px solid #1F2937;
  }

  /* Metric cards */
  [data-testid="metric-container"] {
    background-color: #111827;
    border: 1px solid #1F2937;
    border-radius: 12px;
    padding: 20px 24px;
  }
  [data-testid="metric-container"] label {
    color: #9CA3AF !important;
    font-size: 0.8rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }
  [data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #F9FAFB !important;
    font-size: 1.8rem;
    font-weight: 800;
  }

  /* Feature cards */
  .feature-card {
    background: #111827;
    border: 1px solid #1F2937;
    border-radius: 16px;
    padding: 28px 26px 22px 26px;
    height: 100%;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
  }
  .feature-card:hover {
    border-color: #3B82F6;
    box-shadow: 0 0 0 1px #3B82F6, 0 6px 24px rgba(59,130,246,0.10);
  }
  .feature-icon { font-size: 2.2rem; margin-bottom: 14px; }
  .feature-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: #F9FAFB;
    margin-bottom: 10px;
  }
  .feature-desc {
    font-size: 0.83rem;
    color: #6B7280;
    line-height: 1.65;
    margin-bottom: 0;
  }

  /* Job cards (shared with other pages) */
  .job-card {
    background: #111827;
    border: 1px solid #1F2937;
    border-radius: 14px;
    padding: 20px 22px;
    margin-bottom: 16px;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
  }
  .job-card:hover {
    border-color: #3B82F6;
    box-shadow: 0 0 0 1px #3B82F6, 0 4px 20px rgba(59,130,246,0.12);
  }
  .job-title { font-size: 1.05rem; font-weight: 700; color: #F9FAFB; margin-bottom: 4px; }
  .job-company { font-size: 0.9rem; color: #60A5FA; margin-bottom: 10px; }

  /* Badges */
  .badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
    margin-right: 6px;
    margin-bottom: 4px;
  }
  .badge-source   { background: #1E3A5F; color: #93C5FD; }
  .badge-type     { background: #1A2E1A; color: #86EFAC; }
  .badge-location { background: #2D1F4A; color: #C4B5FD; }
  .badge-remote   { background: #1A2E2E; color: #5EEAD4; }

  /* Tag chips */
  .tag-chip {
    display: inline-block;
    background: #1F2937;
    color: #9CA3AF;
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 0.68rem;
    margin: 2px 3px 2px 0;
  }

  /* Score colours */
  .score-high   { color: #10B981; font-weight: 800; font-size: 1.4rem; }
  .score-medium { color: #F59E0B; font-weight: 800; font-size: 1.4rem; }
  .score-low    { color: #EF4444; font-weight: 800; font-size: 1.4rem; }

  .apply-btn {
    display: inline-block;
    background: #1D4ED8;
    color: #F9FAFB !important;
    text-decoration: none !important;
    border-radius: 8px;
    padding: 6px 16px;
    font-size: 0.8rem;
    font-weight: 600;
    float: right;
    margin-top: -4px;
    transition: background 0.2s;
  }
  .apply-btn:hover { background: #2563EB; }

  .section-header {
    font-size: 1.6rem;
    font-weight: 800;
    color: #F9FAFB;
    margin-bottom: 4px;
    letter-spacing: -0.5px;
  }
  .section-sub { font-size: 0.88rem; color: #6B7280; margin-bottom: 24px; }

  hr { border-color: #1F2937; }

  [data-testid="stFileUploader"] {
    border: 2px dashed #374151;
    border-radius: 14px;
    padding: 20px;
    background: #111827;
  }

  .sidebar-logo {
    font-size: 1.6rem;
    font-weight: 900;
    color: #3B82F6;
    letter-spacing: -1px;
    margin-bottom: 2px;
  }
  .sidebar-tagline { font-size: 0.75rem; color: #4B5563; margin-bottom: 20px; }

  /* page_link buttons */
  [data-testid="stPageLink"] a {
    font-size: 0.85rem !important;
    font-weight: 500 !important;
  }

  /* Stat divider bar */
  .stat-bar {
    height: 3px;
    border-radius: 2px;
    background: linear-gradient(90deg, #3B82F6 0%, #8B5CF6 50%, #10B981 100%);
    margin: 8px 0 28px 0;
  }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-logo">🔍 JobSense</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-tagline">Kenya Jobs Intelligence Platform</div>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("**Navigate**")
    st.page_link("app.py",                    label="🏠  Home")
    st.page_link("pages/01_Browse_Jobs.py",    label="💼  Browse Jobs")
    st.page_link("pages/02_CV_Matcher.py",     label="🎯  CV Matcher")
    st.page_link("pages/03_Pipeline_Stats.py", label="📊  Pipeline Stats")
    st.markdown("---")
    st.markdown(
        '<div style="font-size:0.72rem;color:#374151">Scrapes 8 sources daily · 04:00 EAT</div>',
        unsafe_allow_html=True,
    )

# ── Hero ───────────────────────────────────────────────────────────────────────
API = os.getenv("API_BASE_URL", "http://localhost:8000")

st.markdown('<div class="section-header">Kenya Jobs Intelligence</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-sub">Unified feed from 8 job boards &nbsp;·&nbsp; '
    'Semantic CV matching &nbsp;·&nbsp; AI-powered gap analysis &nbsp;·&nbsp; Daily pipeline</div>',
    unsafe_allow_html=True,
)
st.markdown('<div class="stat-bar"></div>', unsafe_allow_html=True)

# ── KPI metrics ────────────────────────────────────────────────────────────────
try:
    stats = requests.get(f"{API}/api/stats", timeout=5).json()
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Jobs",     f"{stats.get('total_jobs', 0):,}")
    c2.metric("Active Jobs",    f"{stats.get('active_jobs', 0):,}")
    c3.metric("Remote Jobs",    f"{stats.get('remote_jobs', 0):,}")
    c4.metric("AI-Embedded",    f"{stats.get('embedded_jobs', 0):,}")
    c5.metric("Sources",        f"{stats.get('sources', 0)}")
except Exception:
    st.warning("⚠️ API is starting up — refresh in a moment.")

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("---")
st.markdown("<br>", unsafe_allow_html=True)

# ── Feature cards ──────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3, gap="large")

with col1:
    st.markdown("""
    <div class="feature-card">
      <div class="feature-icon">💼</div>
      <div class="feature-title">Browse Jobs</div>
      <div class="feature-desc">
        Search and filter across 8 Kenyan and global job sources.
        Filter by type, location, experience level, and remote status.
        Updated every morning at 07:00 EAT.
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    st.page_link("pages/01_Browse_Jobs.py", label="Browse Jobs →", use_container_width=True)

with col2:
    st.markdown("""
    <div class="feature-card">
      <div class="feature-icon">🎯</div>
      <div class="feature-title">CV Matcher</div>
      <div class="feature-desc">
        Upload your PDF CV and get your top 10 semantically matched jobs.
        Each match is scored by Claude AI with skill gaps and a personalised
        hiring recommendation.
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    st.page_link("pages/02_CV_Matcher.py", label="Match My CV →", use_container_width=True)

with col3:
    st.markdown("""
    <div class="feature-card">
      <div class="feature-icon">📊</div>
      <div class="feature-title">Pipeline Stats</div>
      <div class="feature-desc">
        Live pipeline monitoring — source distribution, embedding coverage,
        trending skills extracted from job tags, and a full scrape audit log
        with per-source run history.
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    st.page_link("pages/03_Pipeline_Stats.py", label="View Stats →", use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("---")

# ── How the CV matching works ──────────────────────────────────────────────────
st.markdown("#### How CV Matching Works")
st.markdown("<br>", unsafe_allow_html=True)

s1, s2, s3, s4 = st.columns(4, gap="medium")
for col, icon, step, desc in [
    (s1, "📄", "1. Extract",  "pdfplumber reads text from your PDF CV — no image scanning required"),
    (s2, "🧠", "2. Embed",    "all-MiniLM-L6-v2 encodes your CV as a 384-dimensional semantic vector"),
    (s3, "🔍", "3. Search",   "pgvector cosine similarity finds the closest matching jobs in the database"),
    (s4, "✨", "4. Analyse",  "Claude Haiku scores each match and returns strengths, gaps, and a recommendation"),
]:
    col.markdown(f"""
    <div style="background:#111827;border:1px solid #1F2937;border-radius:14px;
                padding:22px 18px;text-align:center;height:100%">
      <div style="font-size:1.8rem;margin-bottom:10px">{icon}</div>
      <div style="font-size:0.85rem;font-weight:700;color:#F9FAFB;margin-bottom:8px">{step}</div>
      <div style="font-size:0.78rem;color:#6B7280;line-height:1.55">{desc}</div>
    </div>
    """, unsafe_allow_html=True)
