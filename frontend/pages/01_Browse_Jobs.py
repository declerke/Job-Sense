import os

import requests
import streamlit as st

st.set_page_config(page_title="Browse Jobs — JobSense", layout="wide", page_icon="💼")

API = os.getenv("API_BASE_URL", "http://localhost:8000")

# ── Shared CSS (must repeat on each page) ────────────────────────────────────
st.markdown("""
<style>
  #MainMenu, footer, header {visibility: hidden;}
  .stApp { background-color: #0A0E1A; }
  [data-testid="stSidebar"] { background-color: #0D1117; border-right: 1px solid #1F2937; }
  .job-card {
    background: #111827; border: 1px solid #1F2937; border-radius: 14px;
    padding: 20px 22px; margin-bottom: 16px;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
  }
  .job-card:hover { border-color: #3B82F6; box-shadow: 0 0 0 1px #3B82F6, 0 4px 20px rgba(59,130,246,0.12); }
  .job-title  { font-size: 1.05rem; font-weight: 700; color: #F9FAFB; margin-bottom: 4px; }
  .job-company { font-size: 0.9rem; color: #60A5FA; margin-bottom: 10px; }
  .badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 0.72rem; font-weight: 600; margin-right: 6px; margin-bottom: 4px; }
  .badge-source   { background: #1E3A5F; color: #93C5FD; }
  .badge-type     { background: #1A2E1A; color: #86EFAC; }
  .badge-location { background: #2D1F4A; color: #C4B5FD; }
  .badge-remote   { background: #1A2E2E; color: #5EEAD4; }
  .tag-chip { display: inline-block; background: #1F2937; color: #9CA3AF; border-radius: 6px; padding: 2px 8px; font-size: 0.68rem; margin: 2px 3px 2px 0; }
  .apply-btn { display: inline-block; background: #1D4ED8; color: #F9FAFB !important; text-decoration: none !important; border-radius: 8px; padding: 6px 16px; font-size: 0.8rem; font-weight: 600; float: right; margin-top: -4px; }
  .apply-btn:hover { background: #2563EB; }
  .section-header { font-size: 1.4rem; font-weight: 700; color: #F9FAFB; margin-bottom: 4px; }
  .section-sub { font-size: 0.85rem; color: #6B7280; margin-bottom: 20px; }
  hr { border-color: #1F2937; }
  [data-testid="metric-container"] { background: #111827; border: 1px solid #1F2937; border-radius: 12px; padding: 16px; }
</style>
""", unsafe_allow_html=True)


def render_tags(tags_str: str | None) -> str:
    if not tags_str:
        return ""
    tags = [t.strip() for t in tags_str.split(",") if t.strip()][:8]
    return "".join(f'<span class="tag-chip">{t}</span>' for t in tags)


def render_job_card(job: dict, match_score: int | None = None):
    title    = job.get("title", "Unknown Role")
    company  = job.get("company") or "Unknown Company"
    location = job.get("location") or "Kenya"
    source   = job.get("source", "")
    job_type = job.get("job_type") or ""
    remote   = job.get("remote", False)
    url      = job.get("url") or "#"
    tags     = render_tags(job.get("tags"))

    score_html = ""
    if match_score is not None:
        color = "#10B981" if match_score >= 70 else "#F59E0B" if match_score >= 40 else "#EF4444"
        score_html = f'<span style="float:right;color:{color};font-weight:800;font-size:1.1rem">{match_score}%</span>'

    remote_badge = '<span class="badge badge-remote">🌐 Remote</span>' if remote else ""
    type_badge   = f'<span class="badge badge-type">{job_type}</span>' if job_type else ""

    st.markdown(f"""
    <div class="job-card">
      <div class="job-title">{title} {score_html}</div>
      <div class="job-company">🏢 {company}</div>
      <div style="margin-bottom:10px">
        <span class="badge badge-location">📍 {location}</span>
        {type_badge}
        {remote_badge}
        <span class="badge badge-source">{source}</span>
        <a href="{url}" target="_blank" class="apply-btn">Apply →</a>
      </div>
      <div>{tags}</div>
    </div>
    """, unsafe_allow_html=True)


# ── Sidebar filters ────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔎 Filters")

    search   = st.text_input("Search", placeholder="e.g. data engineer, Python...")
    source   = st.selectbox("Source", ["All", "BrighterMonday", "MyJobMag", "Fuzu",
                                        "Adzuna", "RemoteOK", "CareerPointKenya",
                                        "JobWebKenya", "CorporateStaffing"])
    location = st.text_input("Location", placeholder="e.g. Nairobi")
    job_type = st.selectbox("Job Type", ["All", "full-time", "part-time", "contract",
                                          "internship", "freelance"])
    experience = st.selectbox("Experience", ["All", "entry", "mid", "senior", "executive"])
    remote_only = st.toggle("Remote only", value=False)
    per_page = st.selectbox("Jobs per page", [20, 40, 60], index=0)

    st.markdown("---")
    if st.button("Clear Filters", use_container_width=True):
        st.rerun()

# ── Main content ──────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">💼 Browse Jobs</div>', unsafe_allow_html=True)

if "job_page" not in st.session_state:
    st.session_state.job_page = 1

# Build API params
params: dict = {"page": st.session_state.job_page, "per_page": per_page}
if search:         params["search"]     = search
if source != "All": params["source"]   = source
if location:       params["location"]  = location
if job_type != "All": params["job_type"] = job_type
if experience != "All": params["experience"] = experience
if remote_only:    params["remote"]    = True

# Fetch
try:
    resp = requests.get(f"{API}/api/jobs", params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
except Exception as e:
    st.error(f"Could not reach API: {e}")
    st.stop()

total  = data.get("total", 0)
pages  = data.get("pages", 1)
jobs   = data.get("jobs", [])

# Results summary
col_a, col_b = st.columns([3, 1])
with col_a:
    st.markdown(f'<div class="section-sub">{total:,} jobs found</div>', unsafe_allow_html=True)
with col_b:
    st.markdown(f'<div class="section-sub" style="text-align:right">Page {st.session_state.job_page} of {pages}</div>', unsafe_allow_html=True)

if not jobs:
    st.info("No jobs match your filters. Try broadening the search.")
    st.stop()

# Two-column layout
left_col, right_col = st.columns(2)
for i, job in enumerate(jobs):
    with left_col if i % 2 == 0 else right_col:
        render_job_card(job)

# Pagination
st.markdown("---")
p_prev, _, p_next = st.columns([1, 4, 1])
with p_prev:
    if st.button("← Previous", disabled=st.session_state.job_page <= 1, use_container_width=True):
        st.session_state.job_page -= 1
        st.rerun()
with p_next:
    if st.button("Next →", disabled=st.session_state.job_page >= pages, use_container_width=True):
        st.session_state.job_page += 1
        st.rerun()
