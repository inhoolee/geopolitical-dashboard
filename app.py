"""Geopolitical Risk Dashboard – entry point."""

from datetime import date, timedelta

import streamlit as st

from dashboard.db import get_conn, query
from dashboard.utils import REGION_LABELS, fmt_number
from dashboard import queries as Q

st.set_page_config(
    page_title="Geopolitical Risk Dashboard",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🌍 Geopolitical Risk")
    st.caption("Design Draft · Data through Feb 2026")
    st.divider()

    st.subheader("Filters")
    date_from = st.date_input("From", value=date(2017, 1, 20), min_value=date(1989, 1, 1))
    date_to   = st.date_input("To",   value=date(2026, 2, 28))

    all_regions = list(REGION_LABELS.keys())
    selected_regions = st.multiselect(
        "Regions",
        options=all_regions,
        default=[],
        format_func=lambda k: REGION_LABELS.get(k, k),
        placeholder="All regions",
    )

    st.divider()
    st.subheader("Pipeline state")
    conn = get_conn()
    state_df = query(conn, Q.PIPELINE_STATE)
    for _, row in state_df.iterrows():
        icon = "✅" if row["status"] == "success" else "⚠️" if row["status"] == "partial" else "❌"
        st.caption(f"{icon} **{row['source_name']}** — {row['last_run']}  ({row['records_processed']:,} rows)")

# ── Store filters in session state for pages to read ────────────────────────
st.session_state["date_from"]        = str(date_from)
st.session_state["date_to"]          = str(date_to)
st.session_state["selected_regions"] = selected_regions

# ── Page navigation ──────────────────────────────────────────────────────────
pages = [
    st.Page("pages/01_overview.py",    title="Overview",            icon="🗺️"),
    st.Page("pages/02_incidents.py",   title="Incidents",           icon="⚔️"),
    st.Page("pages/03_diplomatic.py",  title="Diplomatic Actions",  icon="🤝"),
    st.Page("pages/04_risk_score.py",  title="Risk Score",          icon="📊"),
]

pg = st.navigation(pages)
pg.run()
