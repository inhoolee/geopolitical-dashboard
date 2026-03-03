"""Page 2 – Incidents: timeline, regional breakdown, event types, top countries."""

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from dashboard.db import get_conn, query
from dashboard.utils import REGION_LABELS, REGION_COLORS, EVENT_TYPE_COLORS, fmt_number
from dashboard import queries as Q

conn = get_conn()
date_from = st.session_state.get("date_from", "2017-01-20")
date_to   = st.session_state.get("date_to",   "2026-02-28")
sel_regions = st.session_state.get("selected_regions", [])

st.title("⚔️ Incidents")
st.caption(f"Window: **{date_from}** → **{date_to}**")

# ── Weekly timeline ──────────────────────────────────────────────────────────
st.subheader("Weekly Incidents & Fatalities")

if sel_regions and len(sel_regions) == 1:
    weekly = query(conn, Q.WEEKLY_TIMELINE_REGION, [date_from, date_to, sel_regions[0]])
else:
    weekly = query(conn, Q.WEEKLY_TIMELINE, [date_from, date_to])

if not weekly.empty:
    fig_timeline = make_subplots(specs=[[{"secondary_y": True}]])
    fig_timeline.add_trace(
        go.Bar(
            x=weekly["week_start"], y=weekly["incidents"],
            name="Incidents", marker_color="#3B82F6", opacity=0.8,
        ),
        secondary_y=False,
    )
    fig_timeline.add_trace(
        go.Scatter(
            x=weekly["week_start"], y=weekly["fatalities"],
            name="Fatalities", mode="lines",
            line=dict(color="#EF4444", width=2),
            fill="tozeroy", fillcolor="rgba(239,68,68,0.15)",
        ),
        secondary_y=True,
    )
    fig_timeline.update_layout(
        height=320,
        paper_bgcolor="#0F172A",
        plot_bgcolor="#1E293B",
        legend=dict(font=dict(color="#94A3B8")),
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(gridcolor="#334155"),
        hovermode="x unified",
    )
    fig_timeline.update_yaxes(title_text="Incidents", secondary_y=False,
                               gridcolor="#334155", tickfont=dict(color="#94A3B8"))
    fig_timeline.update_yaxes(title_text="Fatalities", secondary_y=True,
                               gridcolor="rgba(0,0,0,0)", tickfont=dict(color="#EF4444"))
    st.plotly_chart(fig_timeline, use_container_width=True)
else:
    st.info("No incident data in selected range.")

st.divider()

# ── Regional breakdown + Event type ─────────────────────────────────────────
col_reg, col_et = st.columns([3, 2])

with col_reg:
    st.subheader("Incidents by Region")
    region_df = query(conn, Q.REGION_BREAKDOWN, [date_from, date_to])
    region_df["region_label"] = region_df["region"].apply(
        lambda r: REGION_LABELS.get(r, r)
    )
    region_df["color"] = region_df["region"].apply(
        lambda r: REGION_COLORS.get(r, "#6B7280")
    )
    if not region_df.empty:
        fig_reg = px.bar(
            region_df,
            x="incidents",
            y="region_label",
            orientation="h",
            color="region",
            color_discrete_map=REGION_COLORS,
            text="incidents",
            hover_data={"fatalities": True, "incidents": True, "region": False},
            labels={"incidents": "Incidents", "region_label": ""},
        )
        fig_reg.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
        fig_reg.update_layout(
            height=320, showlegend=False,
            paper_bgcolor="#0F172A", plot_bgcolor="#1E293B",
            margin=dict(l=0, r=60, t=10, b=0),
            xaxis=dict(gridcolor="#334155"),
            yaxis=dict(gridcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig_reg, use_container_width=True)
    else:
        st.info("No regional data available.")

with col_et:
    st.subheader("Event Types")
    chart_type = st.radio("View as", ["Pie", "Bar"], horizontal=True, label_visibility="collapsed")
    et_df = query(conn, Q.EVENT_TYPE_BREAKDOWN, [date_from, date_to])
    if not et_df.empty:
        if chart_type == "Pie":
            fig_et = px.pie(
                et_df,
                names="event_type",
                values="incident_count",
                color="event_type",
                color_discrete_map=EVENT_TYPE_COLORS,
                hole=0.4,
            )
            fig_et.update_traces(
                textposition="inside",
                textinfo="percent+label",
                hovertemplate="%{label}<br>%{value:,} incidents<extra></extra>",
            )
        else:
            fig_et = px.bar(
                et_df,
                x="incident_count",
                y="event_type",
                orientation="h",
                color="event_type",
                color_discrete_map=EVENT_TYPE_COLORS,
                text="incident_count",
            )
            fig_et.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
            fig_et.update_layout(showlegend=False)

        fig_et.update_layout(
            height=320,
            paper_bgcolor="#0F172A",
            plot_bgcolor="#1E293B",
            margin=dict(l=0, r=60, t=10, b=0),
            legend=dict(font=dict(color="#94A3B8")),
        )
        st.plotly_chart(fig_et, use_container_width=True)
    else:
        st.info("No event type data available.")

st.divider()

# ── Top countries by fatalities ───────────────────────────────────────────────
st.subheader("Top Countries by Fatalities")
top_fat = query(conn, Q.TOP_FATALITIES, [date_from, date_to])
if not top_fat.empty:
    top_fat = top_fat[top_fat["total_fatalities"] > 0].head(15)
    fig_fat = px.bar(
        top_fat,
        x="total_fatalities",
        y="country",
        orientation="h",
        color="total_fatalities",
        color_continuous_scale="Reds",
        text="total_fatalities",
        hover_data={"total_incidents": True, "total_fatalities": True},
        labels={"total_fatalities": "Fatalities", "total_incidents": "Incidents", "country": ""},
    )
    fig_fat.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
    fig_fat.update_layout(
        height=420,
        paper_bgcolor="#0F172A",
        plot_bgcolor="#1E293B",
        showlegend=False,
        coloraxis_showscale=False,
        margin=dict(l=0, r=80, t=10, b=0),
        xaxis=dict(gridcolor="#334155"),
        yaxis=dict(gridcolor="rgba(0,0,0,0)", autorange="reversed"),
    )
    st.plotly_chart(fig_fat, use_container_width=True)
else:
    st.info("No fatality data in selected range.")
