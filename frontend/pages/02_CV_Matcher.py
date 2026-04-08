import os

import requests
import streamlit as st

st.set_page_config(page_title="CV Matcher — JobSense", layout="wide", page_icon="🎯")

API = os.getenv("API_BASE_URL", "http://localhost:8000")

st.markdown("""
<style>
  #MainMenu, footer, header {visibility: hidden;}
  .stApp { background-color: #0A0E1A; }
  [data-testid="stSidebar"] { background-color: #0D1117; border-right: 1px solid #1F2937; }
  .job-card { background: #111827; border: 1px solid #1F2937; border-radius: 14px; padding: 20px 22px; margin-bottom: 16px; transition: border-color 0.2s; }
  .job-card:hover { border-color: #3B82F6; box-shadow: 0 0 0 1px #3B82F6; }
  .job-title  { font-size: 1.05rem; font-weight: 700; color: #F9FAFB; margin-bottom: 4px; }
  .job-company { font-size: 0.9rem; color: #60A5FA; margin-bottom: 10px; }
  .badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 0.72rem; font-weight: 600; margin-right: 6px; }
  .badge-source { background: #1E3A5F; color: #93C5FD; }
  .badge-location { background: #2D1F4A; color: #C4B5FD; }
  .badge-remote { background: #1A2E2E; color: #5EEAD4; }
  .tag-chip { display: inline-block; background: #1F2937; color: #9CA3AF; border-radius: 6px; padding: 2px 8px; font-size: 0.68rem; margin: 2px 3px 2px 0; }
  .skill-match { display: inline-block; background: #052E16; color: #86EFAC; border-radius: 6px; padding: 2px 8px; font-size: 0.7rem; margin: 2px 3px 2px 0; }
  .skill-gap   { display: inline-block; background: #2D0B0B; color: #FCA5A5; border-radius: 6px; padding: 2px 8px; font-size: 0.7rem; margin: 2px 3px 2px 0; }
  .apply-btn { display: inline-block; background: #1D4ED8; color: #F9FAFB !important; text-decoration: none !important; border-radius: 8px; padding: 6px 16px; font-size: 0.8rem; font-weight: 600; float: right; }
  .match-rank { font-size: 0.75rem; color: #6B7280; margin-bottom: 6px; }
  .section-header { font-size: 1.4rem; font-weight: 700; color: #F9FAFB; margin-bottom: 4px; }
  .section-sub { font-size: 0.85rem; color: #6B7280; margin-bottom: 20px; }
  hr { border-color: #1F2937; }
  [data-testid="stFileUploader"] { border: 2px dashed #374151; border-radius: 14px; padding: 20px; background: #111827; }
</style>
""", unsafe_allow_html=True)


def score_color(score: int) -> str:
    if score >= 70:
        return "#10B981"
    elif score >= 40:
        return "#F59E0B"
    return "#EF4444"


def render_match_card(rank: int, match: dict):
    job    = match.get("job", {})
    score  = match.get("match_score", 0)
    sim    = match.get("similarity_score", 0)
    strengths = match.get("strengths", [])
    gaps   = match.get("gaps", [])
    rec    = match.get("recommendation", "")
    url    = job.get("url") or "#"
    color  = score_color(score)

    strengths_html = "".join(f'<span class="skill-match">✓ {s}</span>' for s in strengths)
    gaps_html      = "".join(f'<span class="skill-gap">✗ {g}</span>' for g in gaps)

    st.markdown(f"""
    <div class="job-card">
      <div class="match-rank">Match #{rank}</div>
      <div style="display:flex; justify-content:space-between; align-items:flex-start">
        <div>
          <div class="job-title">{job.get('title', 'Unknown')}</div>
          <div class="job-company">🏢 {job.get('company') or 'Unknown'}</div>
        </div>
        <div style="text-align:center; min-width:70px">
          <div style="font-size:2rem; font-weight:900; color:{color}; line-height:1">{score}</div>
          <div style="font-size:0.65rem; color:#6B7280">/ 100</div>
        </div>
      </div>
      <div style="margin-bottom:10px">
        <span class="badge badge-location">📍 {job.get('location') or 'Kenya'}</span>
        <span class="badge badge-source">{job.get('source', '')}</span>
        {'<span class="badge badge-remote">🌐 Remote</span>' if job.get('remote') else ''}
        <a href="{url}" target="_blank" class="apply-btn">Apply →</a>
      </div>
      <div style="margin-bottom:8px">
        <div style="font-size:0.75rem; color:#6B7280; margin-bottom:4px">Matching skills:</div>
        {strengths_html if strengths_html else '<span style="color:#4B5563;font-size:0.75rem">—</span>'}
      </div>
      <div style="margin-bottom:8px">
        <div style="font-size:0.75rem; color:#6B7280; margin-bottom:4px">Skill gaps:</div>
        {gaps_html if gaps_html else '<span style="color:#4B5563;font-size:0.75rem">—</span>'}
      </div>
      {f'<div style="font-size:0.8rem; color:#9CA3AF; font-style:italic; margin-top:8px; padding-top:8px; border-top:1px solid #1F2937">{rec}</div>' if rec else ''}
      <div style="font-size:0.68rem; color:#374151; margin-top:6px">Semantic similarity: {sim:.1%}</div>
    </div>
    """, unsafe_allow_html=True)


# ── Page ──────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">🎯 CV Matcher</div>', unsafe_allow_html=True)
st.markdown('<div class="section-sub">Upload your PDF CV — get your top 10 job matches ranked by AI with skill gap analysis</div>', unsafe_allow_html=True)

left, right = st.columns([1, 2], gap="large")

with left:
    st.markdown("#### Upload Your CV")
    uploaded = st.file_uploader(
        "Drag & drop or click to upload",
        type=["pdf"],
        label_visibility="collapsed",
    )
    top_k = st.slider("Number of matches", min_value=5, max_value=20, value=10, step=1)

    st.markdown("""
    <div style="background:#111827;border:1px solid #1F2937;border-radius:12px;padding:16px;margin-top:16px">
      <div style="font-size:0.8rem;color:#6B7280;margin-bottom:8px">How it works</div>
      <div style="font-size:0.78rem;color:#9CA3AF;line-height:1.6">
        1️⃣ <b>Extract</b> — text pulled from your PDF<br>
        2️⃣ <b>Embed</b> — CV encoded as a 384-dim semantic vector<br>
        3️⃣ <b>Search</b> — pgvector cosine similarity across all jobs<br>
        4️⃣ <b>Analyse</b> — Claude scores each match, lists strengths & gaps
      </div>
    </div>
    """, unsafe_allow_html=True)

with right:
    if not uploaded:
        st.markdown("""
        <div style="background:#111827;border:2px dashed #1F2937;border-radius:14px;
                    padding:60px 40px;text-align:center;color:#4B5563">
          <div style="font-size:2.5rem;margin-bottom:12px">📄</div>
          <div style="font-size:1rem;color:#6B7280">Your matched jobs will appear here</div>
          <div style="font-size:0.8rem;margin-top:6px">Upload a PDF CV on the left to begin</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        if st.button("🔍  Find My Matches", type="primary", use_container_width=True):
            with st.spinner("Embedding your CV and searching the job database..."):
                try:
                    resp = requests.post(
                        f"{API}/api/cv-match",
                        files={"cv_file": (uploaded.name, uploaded.getvalue(), "application/pdf")},
                        data={"top_k": top_k},
                        timeout=60,
                    )
                    if resp.status_code == 200:
                        st.session_state["match_result"] = resp.json()
                    elif resp.status_code == 503:
                        st.error("No embedded jobs found yet. Run the pipeline first.")
                        st.stop()
                    elif resp.status_code == 422:
                        st.error("Could not read text from your PDF. Make sure it is a text-based (not scanned) PDF.")
                        st.stop()
                    else:
                        st.error(f"API error {resp.status_code}: {resp.text[:200]}")
                        st.stop()
                except requests.exceptions.Timeout:
                    st.error("Request timed out. The embedding model may still be loading — try again in 30 seconds.")
                    st.stop()
                except Exception as e:
                    st.error(f"Could not reach API: {e}")
                    st.stop()

        result = st.session_state.get("match_result")
        if result:
            matches = result.get("matches", [])
            model   = result.get("model_used", "")
            cv_sum  = result.get("cv_summary", "")

            st.markdown(f"""
            <div style="background:#0F1F0F;border:1px solid #166534;border-radius:10px;
                        padding:12px 16px;margin-bottom:16px">
              <span style="font-size:0.8rem;color:#86EFAC">
                ✅ Found {len(matches)} matches · Model: <b>{model}</b>
              </span>
            </div>
            """, unsafe_allow_html=True)

            for i, match in enumerate(matches, 1):
                render_match_card(i, match)
