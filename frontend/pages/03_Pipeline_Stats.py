import os
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

st.set_page_config(page_title="Pipeline Stats — JobSense", layout="wide", page_icon="📊")

API = os.getenv("API_BASE_URL", "http://localhost:8000")

st.markdown("""
<style>
  #MainMenu, footer, header {visibility: hidden;}
  .stApp { background-color: #0A0E1A; }
  [data-testid="stSidebar"] { background-color: #0D1117; border-right: 1px solid #1F2937; }
  [data-testid="metric-container"] { background: #111827; border: 1px solid #1F2937; border-radius: 12px; padding: 16px; }
  [data-testid="metric-container"] label { color: #9CA3AF !important; font-size: 0.8rem; }
  [data-testid="metric-container"] [data-testid="stMetricValue"] { color: #F9FAFB !important; font-size: 1.5rem; font-weight: 700; }
  .section-header { font-size: 1.4rem; font-weight: 700; color: #F9FAFB; margin-bottom: 4px; }
  .section-sub { font-size: 0.85rem; color: #6B7280; margin-bottom: 20px; }
  hr { border-color: #1F2937; }
  .chart-card { background: #111827; border: 1px solid #1F2937; border-radius: 14px; padding: 20px; margin-bottom: 16px; }
</style>
""", unsafe_allow_html=True)

PLOTLY_TEMPLATE = dict(
    layout=dict(
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font=dict(color="#9CA3AF", size=12),
        title_font=dict(color="#F9FAFB", size=14),
        xaxis=dict(gridcolor="#1F2937", linecolor="#374151"),
        yaxis=dict(gridcolor="#1F2937", linecolor="#374151"),
        legend=dict(bgcolor="#111827", bordercolor="#1F2937"),
    )
)


@st.cache_data(ttl=60)
def fetch(endpoint: str) -> dict | list:
    try:
        r = requests.get(f"{API}{endpoint}", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}


# ── Page ──────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">📊 Pipeline Stats</div>', unsafe_allow_html=True)
st.markdown('<div class="section-sub">Live metrics from the JobSense scraping pipeline</div>', unsafe_allow_html=True)

# KPI row
stats = fetch("/api/stats")
if stats:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Jobs",   f"{stats.get('total_jobs', 0):,}")
    c2.metric("Active Jobs",  f"{stats.get('active_jobs', 0):,}")
    c3.metric("AI-Embedded",  f"{stats.get('embedded_jobs', 0):,}")
    c4.metric("Remote Jobs",  f"{stats.get('remote_jobs', 0):,}")
    c5.metric("Sources",      stats.get("sources", 0))

    last = stats.get("last_scraped")
    if last:
        st.caption(f"Last pipeline run: {last[:19].replace('T', ' ')} UTC")
else:
    st.warning("Could not load stats — is the API running?")

st.markdown("---")

# Source breakdown + embedding coverage
sources_data = fetch("/api/sources")
col1, col2 = st.columns(2)

with col1:
    st.markdown("#### Jobs by Source")
    if sources_data:
        df = pd.DataFrame(sources_data)
        fig = px.bar(
            df, x="total_jobs", y="source", orientation="h",
            color="active_jobs",
            color_continuous_scale=[[0, "#1D4ED8"], [1, "#3B82F6"]],
            labels={"total_jobs": "Total", "source": "", "active_jobs": "Active"},
            template="plotly_dark",
        )
        fig.update_layout(**PLOTLY_TEMPLATE["layout"], showlegend=False, coloraxis_showscale=False,
                          margin=dict(l=0, r=0, t=10, b=0), height=280)
        fig.update_traces(marker_line_width=0)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No source data yet.")

with col2:
    st.markdown("#### Embedding Coverage by Source")
    if sources_data:
        df = pd.DataFrame(sources_data)
        df["pct_embedded"] = (df["embedded_jobs"] / df["total_jobs"].replace(0, 1) * 100).round(1)
        fig = px.bar(
            df, x="pct_embedded", y="source", orientation="h",
            color="pct_embedded",
            color_continuous_scale=[[0, "#7C3AED"], [1, "#A78BFA"]],
            labels={"pct_embedded": "% Embedded", "source": ""},
            template="plotly_dark",
        )
        fig.update_layout(**PLOTLY_TEMPLATE["layout"], showlegend=False, coloraxis_showscale=False,
                          margin=dict(l=0, r=0, t=10, b=0), height=280)
        fig.update_layout(xaxis_range=[0, 100])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No embedding data yet.")

st.markdown("---")

# Scrape logs table
st.markdown("#### Recent Scrape History")
logs = fetch("/api/scrape-logs?limit=30")
if logs:
    df_logs = pd.DataFrame(logs)
    keep = ["started_at", "source", "status", "jobs_found", "jobs_new", "jobs_updated", "jobs_embedded", "duration_seconds"]
    df_logs = df_logs[[c for c in keep if c in df_logs.columns]]
    df_logs.columns = [c.replace("_", " ").title() for c in df_logs.columns]

    def colour_status(val):
        if val == "success":   return "color: #86EFAC"
        if val == "failed":    return "color: #FCA5A5"
        if val == "partial":   return "color: #FDE68A"
        return ""

    st.dataframe(
        df_logs.style.applymap(colour_status, subset=["Status"]),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No scrape logs yet — run the pipeline first.")

st.markdown("---")

# Job type distribution
st.markdown("#### Job Type Distribution")
try:
    jobs_resp = requests.get(f"{API}/api/jobs", params={"per_page": 100}, timeout=10).json()
    jobs_list = jobs_resp.get("jobs", [])
    if jobs_list:
        df_jt = pd.DataFrame(jobs_list)
        type_counts = df_jt["job_type"].fillna("Not Specified").value_counts().reset_index()
        type_counts.columns = ["Job Type", "Count"]
        fig = px.pie(
            type_counts, names="Job Type", values="Count",
            color_discrete_sequence=px.colors.qualitative.Pastel,
            template="plotly_dark",
        )
        fig.update_layout(**PLOTLY_TEMPLATE["layout"], height=320,
                          margin=dict(l=0, r=0, t=10, b=0))
        fig.update_traces(textfont_color="#F9FAFB")
        st.plotly_chart(fig, use_container_width=True)
except Exception:
    st.info("Job type data unavailable.")
