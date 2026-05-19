import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime

from services.github_api import fetch_repo_data, load_demo_data
from services.sentiment import analyze_sentiment
from services.risk_model import compute_risk_score
from services.ai_insights import generate_insights_streaming
from utils.helpers import (
    parse_repo_url, format_risk_badge, days_since,
    stale_pr_count, bus_factor, commit_frequency_last_n_days,
)

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Silent Failure Detector",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Syne:wght@400;600;800&display=swap');

  html, body, [class*="css"] { font-family: 'Syne', sans-serif; }
  code, pre, .stCode { font-family: 'JetBrains Mono', monospace !important; }

  .main-title {
    font-size: 2.4rem; font-weight: 800; letter-spacing: -0.5px;
    background: linear-gradient(135deg, #FF4444 0%, #FF8C00 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 0.2rem;
  }
  .subtitle { color: #888; font-size: 0.95rem; margin-bottom: 2rem; }

  .risk-gauge-container { text-align: center; }

  .metric-chip {
    background: #111; border: 1px solid #222; border-radius: 8px;
    padding: 1rem; margin-bottom: 0.5rem;
  }
  .bottleneck-card {
    border-left: 3px solid #FF4444; background: #0d0d0d;
    padding: 0.6rem 0.9rem; border-radius: 0 8px 8px 0;
    margin-bottom: 0.5rem; font-size: 0.88rem;
  }
  .bottleneck-card.medium { border-left-color: #FB8C00; }
  .bottleneck-card.low { border-left-color: #FDD835; }

  [data-testid="stSidebar"] { background: #0a0a0a; border-right: 1px solid #1a1a1a; }
  .stButton > button {
    width: 100%; background: linear-gradient(135deg, #FF4444, #FF8C00);
    color: white; border: none; border-radius: 8px; font-weight: 600;
    font-family: 'Syne', sans-serif; padding: 0.6rem;
  }
  .stButton > button:hover { opacity: 0.9; }
  div[data-testid="metric-container"] {
    background: #0d0d0d; border: 1px solid #1e1e1e;
    border-radius: 10px; padding: 1rem;
  }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔍 Silent Failure Detector")
    st.markdown("---")

    mode = st.radio("Data source", ["Demo mode", "Live GitHub repo"], index=0)

    github_token = None
    repo_input   = None

    if mode == "Live GitHub repo":
        repo_input = st.text_input(
            "GitHub repo (owner/repo or URL)",
            placeholder="e.g. facebook/react",
        )
        github_token = st.text_input(
            "GitHub token (optional, for private repos)",
            type="password",
            help="Increases rate limit from 60 to 5000 req/hr",
        )

    analyze_btn = st.button("⚡ Analyse Project")

    st.markdown("---")
    st.markdown("**About**")
    st.caption(
        "This tool analyses GitHub activity, PR health, issue patterns, "
        "and communication sentiment to compute a real-time project failure risk score."
    )


# ── Header ───────────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">Silent Failure Detector</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">AI-powered early warning system for software project health</div>',
    unsafe_allow_html=True,
)

# ── State ────────────────────────────────────────────────────────────────────
if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False
if "data" not in st.session_state:
    st.session_state.data = None


# ── Analysis trigger ─────────────────────────────────────────────────────────
if analyze_btn:
    with st.spinner("Fetching data…"):
        if mode == "Demo mode":
            data = load_demo_data()
        else:
            if not repo_input:
                st.error("Please enter a repository.")
                st.stop()
            parsed = parse_repo_url(repo_input)
            if not parsed:
                st.error("Invalid repo format. Use 'owner/repo' or a GitHub URL.")
                st.stop()
            owner, repo = parsed
            data = fetch_repo_data(owner, repo, token=github_token or None)
            if "error" in data:
                st.error(f"GitHub API error: {data['error']}")
                st.stop()

    with st.spinner("Running sentiment analysis…"):
        sentiment = analyze_sentiment(data.get("pr_comments", []))

    with st.spinner("Computing risk score…"):
        risk = compute_risk_score(data, sentiment)

    st.session_state.data      = data
    st.session_state.sentiment = sentiment
    st.session_state.risk      = risk
    st.session_state.analysis_done = True


# ── Dashboard ─────────────────────────────────────────────────────────────────
if st.session_state.analysis_done:
    data      = st.session_state.data
    sentiment = st.session_state.sentiment
    risk      = st.session_state.risk

    repo_info    = data.get("repo", {})
    commits      = data.get("commits", [])
    prs          = data.get("pull_requests", [])
    issues       = data.get("issues", [])
    contributors = data.get("contributors", [])

    # ── Banner ────────────────────────────────────────────────────────────────
    badge = format_risk_badge(risk["label"])
    st.markdown(f"## {badge} {repo_info.get('name', 'Repository')} — {risk['label']} Risk")
    st.caption(repo_info.get("description", ""))

    # ── Top KPIs ─────────────────────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Overall Risk", f"{risk['overall']}/100")
    k2.metric("Commit Freq (30d)", f"{commit_frequency_last_n_days(commits)}/wk")
    k3.metric("Stale PRs", stale_pr_count(prs))
    k4.metric("Open Issues", len([i for i in issues if i.get("state") == "open"]))
    k5.metric("Bus Factor", bus_factor(contributors))

    st.divider()

    # ── Main layout ───────────────────────────────────────────────────────────
    left, right = st.columns([1.1, 1.9], gap="large")

    with left:
        # Risk gauge
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=risk["overall"],
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": "Failure Risk Score", "font": {"size": 14, "color": "#aaa"}},
            number={"font": {"size": 36, "color": risk["color"]}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#444", "tickfont": {"color": "#666"}},
                "bar": {"color": risk["color"], "thickness": 0.25},
                "bgcolor": "#111",
                "bordercolor": "#222",
                "steps": [
                    {"range": [0, 15],  "color": "#0a1f0a"},
                    {"range": [15, 35], "color": "#1a1a00"},
                    {"range": [35, 55], "color": "#1a1000"},
                    {"range": [55, 75], "color": "#1a0a00"},
                    {"range": [75, 100],"color": "#1a0000"},
                ],
                "threshold": {"line": {"color": risk["color"], "width": 3}, "value": risk["overall"]},
            },
        ))
        fig_gauge.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=20, b=10, l=20, r=20),
            height=240,
            font={"family": "Syne"},
        )
        st.plotly_chart(fig_gauge, use_container_width=True)

        st.markdown(f"**Trend:** `{risk['trend'].upper()}`")
        st.markdown(f"**Sentiment:** `{sentiment['sentiment_label'].upper()}`"
                    f" — {sentiment['negative_signal_count']} stress signals detected")

        st.markdown("#### Top Bottlenecks")
        bottlenecks = risk.get("bottlenecks", [])
        if bottlenecks:
            for b in bottlenecks:
                score = b["score"]
                cls = "bottleneck-card" if score >= 70 else (
                      "bottleneck-card medium" if score >= 50 else "bottleneck-card low")
                st.markdown(
                    f'<div class="{cls}">🔺 {b["message"]}<br>'
                    f'<small style="color:#666">Score: {score}/100</small></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.success("No critical bottlenecks detected.")

    with right:
        tab1, tab2, tab3, tab4 = st.tabs(["📈 Commit Activity", "🔀 Pull Requests", "🐛 Issues", "👥 Team"])

        # ── Tab 1: Commits ────────────────────────────────────────────────────
        with tab1:
            if commits:
                df_commits = pd.DataFrame(commits)
                df_commits["date"] = pd.to_datetime(df_commits["date"])
                fig = px.bar(
                    df_commits, x="date", y="count",
                    color_discrete_sequence=["#FF8C00"],
                    labels={"date": "Date", "count": "Commits"},
                )
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(gridcolor="#1a1a1a", color="#666"),
                    yaxis=dict(gridcolor="#1a1a1a", color="#666"),
                    margin=dict(t=10, b=0, l=0, r=0), height=280,
                    font={"family": "Syne"},
                )
                st.plotly_chart(fig, use_container_width=True)

                # Dimension score bar
                decay_score = risk["dimensions"]["commit_decay"]
                st.markdown(f"**Commit decay risk:** {decay_score}/100")
                st.progress(int(decay_score) / 100)
            else:
                st.info("No commit data available.")

        # ── Tab 2: PRs ────────────────────────────────────────────────────────
        with tab2:
            open_prs   = [pr for pr in prs if pr.get("state") == "open"]
            closed_prs = [pr for pr in prs if pr.get("state") == "closed"]

            c1, c2 = st.columns(2)
            c1.metric("Open PRs",   len(open_prs))
            c2.metric("Closed PRs", len(closed_prs))

            if open_prs:
                df_prs = pd.DataFrame(open_prs)
                df_prs["days_stale"] = df_prs["updated_at"].apply(days_since)
                df_prs = df_prs.sort_values("days_stale", ascending=False)
                st.dataframe(
                    df_prs[["number", "title", "author", "comments", "days_stale"]].rename(columns={
                        "number": "#", "title": "Title", "author": "Author",
                        "comments": "Comments", "days_stale": "Days since update",
                    }),
                    use_container_width=True, hide_index=True,
                )

            stag_score = risk["dimensions"]["pr_stagnation"]
            st.markdown(f"**PR stagnation risk:** {stag_score}/100")
            st.progress(int(stag_score) / 100)

        # ── Tab 3: Issues ─────────────────────────────────────────────────────
        with tab3:
            open_issues = [i for i in issues if i.get("state") == "open"]
            if open_issues:
                df_issues = pd.DataFrame(open_issues)
                df_issues["days_open"] = df_issues["created_at"].apply(days_since)
                df_issues["labels_str"] = df_issues["labels"].apply(lambda x: ", ".join(x) if x else "—")
                st.dataframe(
                    df_issues[["number", "title", "comments", "days_open", "labels_str"]].rename(columns={
                        "number": "#", "title": "Title", "comments": "Comments",
                        "days_open": "Days open", "labels_str": "Labels",
                    }),
                    use_container_width=True, hide_index=True,
                )
            else:
                st.success("No open issues.")

            issue_score = risk["dimensions"]["issue_backlog"]
            st.markdown(f"**Issue backlog risk:** {issue_score}/100")
            st.progress(int(issue_score) / 100)

        # ── Tab 4: Team ───────────────────────────────────────────────────────
        with tab4:
            if contributors:
                df_contrib = pd.DataFrame(contributors)
                fig_c = px.bar(
                    df_contrib.sort_values("contributions", ascending=True),
                    x="contributions", y="login", orientation="h",
                    color="contributions",
                    color_continuous_scale=["#FF4444", "#FF8C00", "#FDD835"],
                    labels={"contributions": "Contributions", "login": "Contributor"},
                )
                fig_c.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(gridcolor="#1a1a1a", color="#666"),
                    yaxis=dict(gridcolor="#1a1a1a", color="#666"),
                    coloraxis_showscale=False,
                    margin=dict(t=10, b=0, l=0, r=0), height=260,
                    font={"family": "Syne"},
                )
                st.plotly_chart(fig_c, use_container_width=True)

            diseng_score = risk["dimensions"]["contributor_disengagement"]
            st.markdown(f"**Contributor disengagement risk:** {diseng_score}/100")
            st.progress(int(diseng_score) / 100)

    st.divider()

    # ── Radar chart: all dimensions ───────────────────────────────────────────
    st.subheader("Risk Profile — All Dimensions")
    dims   = risk["dimensions"]
    labels = ["Commit Decay", "PR Stagnation", "Issue Backlog", "Contributor\nDisengagement", "Sentiment"]
    values = [
        dims["commit_decay"], dims["pr_stagnation"], dims["issue_backlog"],
        dims["contributor_disengagement"], dims["sentiment_risk"],
    ]
    fig_radar = go.Figure(go.Scatterpolar(
        r=values + [values[0]],
        theta=labels + [labels[0]],
        fill="toself",
        fillcolor="rgba(255,68,68,0.15)",
        line=dict(color="#FF4444", width=2),
        marker=dict(color="#FF8C00", size=6),
    ))
    fig_radar.update_layout(
        polar=dict(
            bgcolor="#0d0d0d",
            radialaxis=dict(visible=True, range=[0, 100], gridcolor="#222", color="#555"),
            angularaxis=dict(gridcolor="#222", color="#888"),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        margin=dict(t=20, b=20, l=40, r=40),
        height=340,
        font={"family": "Syne"},
    )
    st.plotly_chart(fig_radar, use_container_width=True)

    st.divider()

    # ── AI Insights ───────────────────────────────────────────────────────────
    st.subheader("🤖 AI-Powered Recommendations")
    st.caption("Generated by Claude based on the signals above")

    with st.spinner("Generating insights…"):
        insight_placeholder = st.empty()
        full_text = ""
        try:
            for chunk in generate_insights_streaming(risk, sentiment, data):
                full_text += chunk
                insight_placeholder.markdown(full_text + "▌")
            insight_placeholder.markdown(full_text)
        except Exception as e:
            insight_placeholder.warning(
                f"AI insights unavailable (set ANTHROPIC_API_KEY env var). Error: {e}"
            )

    # ── Sentiment breakdown ───────────────────────────────────────────────────
    if sentiment.get("breakdown"):
        with st.expander("💬 PR Comment Sentiment Breakdown"):
            for item in sentiment["breakdown"]:
                color = {"positive": "#43A047", "negative": "#E53935"}.get(item["label"], "#888")
                st.markdown(
                    f'<span style="color:{color}; font-size:0.8rem;">[{item["label"].upper()}]</span> '
                    f'<span style="font-size:0.88rem;">{item["text"]}</span>',
                    unsafe_allow_html=True,
                )

else:
    # ── Empty state ───────────────────────────────────────────────────────────
    st.markdown("""
    <div style="text-align:center; padding: 4rem 0; color: #555;">
      <div style="font-size: 3rem; margin-bottom: 1rem;">🔍</div>
      <div style="font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem;">
        Ready to detect silent failures
      </div>
      <div style="font-size: 0.9rem;">
        Select <strong>Demo mode</strong> or enter a GitHub repo in the sidebar, then click <strong>Analyse Project</strong>.
      </div>
    </div>
    """, unsafe_allow_html=True)
