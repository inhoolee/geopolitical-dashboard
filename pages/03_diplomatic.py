"""Page 3 – Diplomatic Actions: sanctions by country, seed event timeline."""

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.db import get_conn, query
from dashboard.utils import ACTION_TYPE_COLORS, fmt_number
from dashboard import queries as Q

conn = get_conn()
date_from = st.session_state.get("date_from", "2017-01-20")
date_to   = st.session_state.get("date_to",   "2026-02-28")

st.title("🤝 Diplomatic Actions")

# ── Summary KPIs ─────────────────────────────────────────────────────────────
actions_df = query(conn, Q.SEED_EVENTS_TIMELINE)
sanctions_df = query(conn, Q.SANCTIONS_BY_COUNTRY)

c1, c2, c3 = st.columns(3)
c1.metric("Curated Events (seed)", len(actions_df))
c2.metric("OFAC Sanction Designations", fmt_number(sanctions_df["total_sanctions"].sum()))
c3.metric("Sanctioned Countries", len(sanctions_df))
st.divider()

# ── Top row: sanctions bar + choropleth ──────────────────────────────────────
st.subheader("OFAC Sanction Designations by Target Country")
st.caption("⚠️ Dates are ingestion-date only (OFAC CSV has no historical designation dates). "
           "Counts reflect the current SDN list snapshot.")

sanc_col, map_col = st.columns([2, 3])

with sanc_col:
    top_sanc = sanctions_df.head(15)
    fig_sanc = px.bar(
        top_sanc,
        x="total_sanctions",
        y="country_name",
        orientation="h",
        color="active_sanctions",
        color_continuous_scale="Reds",
        text="total_sanctions",
        hover_data={"active_sanctions": True, "total_sanctions": True},
        labels={"total_sanctions": "Total", "active_sanctions": "Active", "country_name": ""},
    )
    fig_sanc.update_traces(texttemplate="%{text:,}", textposition="outside")
    fig_sanc.update_layout(
        height=460, showlegend=False, coloraxis_showscale=False,
        paper_bgcolor="#0F172A", plot_bgcolor="#1E293B",
        margin=dict(l=0, r=60, t=0, b=0),
        xaxis=dict(gridcolor="#334155"),
        yaxis=dict(gridcolor="rgba(0,0,0,0)", autorange="reversed"),
    )
    st.plotly_chart(fig_sanc, use_container_width=True)

with map_col:
    fig_smap = px.choropleth(
        sanctions_df,
        locations="target",
        locationmode="ISO-3",
        color="total_sanctions",
        hover_name="country_name",
        hover_data={"total_sanctions": True, "active_sanctions": True},
        color_continuous_scale="Reds",
        labels={"total_sanctions": "SDN designations"},
    )
    fig_smap.update_layout(
        height=460,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="#0F172A",
        geo=dict(
            showframe=False, showcoastlines=True, coastlinecolor="#334155",
            showland=True, landcolor="#1E293B",
            showocean=True, oceancolor="#0F172A",
            bgcolor="#0F172A",
        ),
        coloraxis_colorbar=dict(
            title=dict(text="SDN count", font=dict(color="#94A3B8")),
            tickfont=dict(color="#94A3B8"),
        ),
    )
    st.plotly_chart(fig_smap, use_container_width=True)

st.divider()

# ── Diplomatic event timeline (swim-lane scatter) ────────────────────────────
st.subheader("Major Diplomatic Events Timeline (2017–2026)")
st.caption("41 curated events from the deep-research report. Source links available in table below.")

if not actions_df.empty:
    actions_df["display_label"] = actions_df["instrument_name"].str[:55]
    actions_df["actor_target"] = actions_df.apply(
        lambda r: " → ".join(filter(None, [r["actor_iso3"], r["target_iso3"]])), axis=1
    )
    # Filter to date window
    mask = (
        (actions_df["action_date"] >= date_from) &
        (actions_df["action_date"] <= date_to)
    )
    filtered = actions_df[mask]

    if not filtered.empty:
        fig_tl = px.scatter(
            filtered,
            x="action_date",
            y="action_type",
            color="action_type",
            color_discrete_map=ACTION_TYPE_COLORS,
            symbol="status",
            size_max=16,
            hover_data={
                "display_label": True,
                "actor_target": True,
                "region": True,
                "action_type": False,
            },
            hover_name="display_label",
            labels={"action_date": "Date", "action_type": "Event Type"},
        )
        fig_tl.update_traces(marker=dict(size=14, line=dict(width=1, color="#1E293B")))
        fig_tl.update_layout(
            height=380,
            paper_bgcolor="#0F172A",
            plot_bgcolor="#1E293B",
            legend=dict(font=dict(color="#94A3B8"), bgcolor="#1E293B"),
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(gridcolor="#334155", title=""),
            yaxis=dict(gridcolor="#334155", title="", categoryorder="total ascending"),
        )
        st.plotly_chart(fig_tl, use_container_width=True)
    else:
        st.info("No diplomatic events in the selected date range.")

    st.divider()

    # ── Detail table ─────────────────────────────────────────────────────────
    st.subheader("Event Detail")
    display_cols = ["action_date", "actor_iso3", "target_iso3",
                    "action_type", "action_subtype", "instrument_name",
                    "status", "region", "notes", "source_url"]
    st.dataframe(
        filtered[display_cols].rename(columns={
            "action_date": "Date", "actor_iso3": "Actor", "target_iso3": "Target",
            "action_type": "Type", "action_subtype": "Subtype",
            "instrument_name": "Instrument", "status": "Status",
            "region": "Region", "notes": "Notes", "source_url": "Source",
        }),
        hide_index=True,
        use_container_width=True,
        column_config={
            "Source": st.column_config.LinkColumn("Source"),
        },
    )
