"""Page 1 – Overview: KPIs, choropleth map, top movers, diplomatic feed."""

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.db import get_conn, query
from dashboard.utils import grs_band, fmt_number, REGION_LABELS
from dashboard import queries as Q

conn = get_conn()
date_from = st.session_state.get("date_from", "2017-01-20")
date_to   = st.session_state.get("date_to",   "2026-02-28")

st.title("🗺️ Overview")
st.caption(f"Incident window: **{date_from}** → **{date_to}**")

# ── KPI tiles ────────────────────────────────────────────────────────────────
kpi = query(conn, Q.KPI_GLOBAL, [date_from, date_to]).iloc[0]

# Prior period of equal length for delta
from datetime import date, timedelta
d0 = date.fromisoformat(date_from)
d1 = date.fromisoformat(date_to)
span = (d1 - d0).days
prior_from = str(d0 - timedelta(days=span))
prior_to   = str(d0 - timedelta(days=1))
kpi_prior  = query(conn, Q.KPI_GLOBAL, [prior_from, prior_to]).iloc[0]

c1, c2, c3, c4 = st.columns(4)
with c1:
    delta = int(kpi["total_incidents"] or 0) - int(kpi_prior["total_incidents"] or 0)
    st.metric("Total Incidents", fmt_number(kpi["total_incidents"]), delta=fmt_number(delta))
with c2:
    delta = int(kpi["total_fatalities"] or 0) - int(kpi_prior["total_fatalities"] or 0)
    st.metric("Total Fatalities", fmt_number(kpi["total_fatalities"]), delta=fmt_number(delta))
with c3:
    delta = int(kpi["countries_affected"] or 0) - int(kpi_prior["countries_affected"] or 0)
    st.metric("Countries Affected", fmt_number(kpi["countries_affected"]), delta=fmt_number(delta))
with c4:
    delta = int(kpi["civilian_incidents"] or 0) - int(kpi_prior["civilian_incidents"] or 0)
    st.metric("Civilian Incidents", fmt_number(kpi["civilian_incidents"]), delta=fmt_number(delta))

st.divider()

# ── Main row: map + right panel ───────────────────────────────────────────────
map_col, right_col = st.columns([3, 1], gap="medium")

with map_col:
    st.subheader("Geopolitical Risk Score (GRS) — Latest scored month per country")
    grs_df = query(conn, Q.CHOROPLETH_GRS)

    fig_map = px.choropleth(
        grs_df,
        locations="country_iso3",
        locationmode="ISO-3",
        color="grs_score",
        hover_name="country_name",
        hover_data={
            "country_iso3": False,
            "grs_score": ":.1f",
            "score_month": True,
            "coverage_flag": True,
        },
        color_continuous_scale="YlOrRd",
        range_color=(0, 60),
        labels={"grs_score": "GRS (0–100)"},
    )
    fig_map.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="#0F172A",
        geo=dict(
            showframe=False,
            showcoastlines=True,
            coastlinecolor="#334155",
            showland=True,
            landcolor="#1E293B",
            showocean=True,
            oceancolor="#0F172A",
            bgcolor="#0F172A",
            projection_type="natural earth",
        ),
        coloraxis_colorbar=dict(
            title=dict(text="GRS", font=dict(color="#94A3B8")),
            tickfont=dict(color="#94A3B8"),
        ),
        height=440,
    )
    st.plotly_chart(fig_map, use_container_width=True)

    # Top-10 table below map
    st.subheader("Top 10 Highest-Risk Countries")
    top10 = query(conn, Q.TOP10_RISK)
    top10["risk_band"] = top10["grs_score"].apply(lambda s: grs_band(s)[0])
    st.dataframe(
        top10.rename(columns={
            "country": "Country", "grs_score": "GRS Score",
            "risk_band": "Risk Band", "coverage_flag": "Coverage", "as_of": "Scored Month",
        }),
        hide_index=True,
        use_container_width=True,
        column_config={
            "GRS Score": st.column_config.ProgressColumn(
                "GRS Score", min_value=0, max_value=100, format="%.1f"
            ),
        },
    )

with right_col:
    # Top Movers
    st.subheader("📈 Top Movers (MoM Δ)")
    movers = query(conn, Q.TOP_MOVERS)
    if not movers.empty:
        for _, row in movers.head(8).iterrows():
            delta_val = row["delta"]
            arrow = "🔴 ▲" if delta_val > 0 else "🟢 ▼" if delta_val < 0 else "⚪ –"
            st.markdown(
                f"{arrow} **{row['country']}** &nbsp; GRS {row['grs']:g} "
                f"({'+'if delta_val>0 else ''}{delta_val:g})",
                unsafe_allow_html=True,
            )
    else:
        st.caption("No trend data available.")

    st.divider()

    # Diplomatic feed
    st.subheader("🤝 Recent Diplomatic Events")
    feed = query(conn, Q.DIPLOMATIC_FEED)
    if not feed.empty:
        for _, row in feed.head(10).iterrows():
            actors = " → ".join(filter(None, [row["actor"], row["target"]]))
            status_icon = {"active": "🟡", "completed": "⚫", "reversed": "🟢"}.get(
                str(row["status"]).lower(), "⚪"
            )
            st.markdown(
                f"**{row['action_date']}** {status_icon}  \n"
                f"{row['instrument_name'][:60]}  \n"
                f"<small>{actors} · {row['action_type']}</small>",
                unsafe_allow_html=True,
            )
            st.caption("")
    else:
        st.caption("No diplomatic events in range.")
