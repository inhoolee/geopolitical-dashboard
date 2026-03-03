"""Page 4 – Risk Score: GRS driver heatmap and country drilldown."""

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import streamlit as st

from dashboard.db import get_conn, query
from dashboard.utils import (
    DRIVER_LABELS, DRIVER_WEIGHTS, grs_band, fmt_number
)
from dashboard import queries as Q

conn = get_conn()

st.title("📊 Risk Score")
st.caption(
    "Composite Geopolitical Risk Score (GRS) — 0 to 100. "
    "Drivers: Conflict incidents (22.5%), Conflict fatalities (22.5%), "
    "Sanctions (20%), Militarization (15%), News tension (10%)."
)

# ── Heatmap ──────────────────────────────────────────────────────────────────
grs_df = query(conn, Q.GRS_HEATMAP)

top_n = st.slider("Countries displayed", min_value=10, max_value=40, value=25, step=5)
grs_top = grs_df.head(top_n).copy()

driver_cols = list(DRIVER_LABELS.keys())
driver_names = [DRIVER_LABELS[c] for c in driver_cols]

z = grs_top[driver_cols].values
y = grs_top["country_name"].tolist()

fig_heat = go.Figure(go.Heatmap(
    z=z,
    x=driver_names,
    y=y,
    colorscale="YlOrRd",
    zmin=0, zmax=1,
    text=[[f"{v:.2f}" for v in row] for row in z],
    texttemplate="%{text}",
    textfont=dict(size=9, color="white"),
    hovertemplate="<b>%{y}</b><br>%{x}: %{z:.3f}<extra></extra>",
))

# Overlay composite GRS score as annotation on the right edge
for i, (_, row) in enumerate(grs_top.iterrows()):
    band, color = grs_band(row["grs_score"])
    fig_heat.add_annotation(
        x=len(driver_names) - 0.5 + 0.7,
        y=i,
        text=f"<b>{row['grs_score']:.0f}</b>",
        showarrow=False,
        font=dict(size=10, color=color),
        xref="x", yref="y",
    )

fig_heat.update_layout(
    height=max(400, top_n * 22),
    paper_bgcolor="#0F172A",
    plot_bgcolor="#1E293B",
    margin=dict(l=0, r=80, t=30, b=0),
    xaxis=dict(side="top", tickfont=dict(color="#94A3B8"), gridcolor="#334155"),
    yaxis=dict(
        tickfont=dict(color="#94A3B8"),
        autorange="reversed",
        gridcolor="#334155",
    ),
    coloraxis_colorbar=dict(
        title="Score",
        tickfont=dict(color="#94A3B8"),
        titlefont=dict(color="#94A3B8"),
    ),
    title=dict(
        text="GRS Driver Scores (0–1 normalised) — numbers on right = composite GRS",
        font=dict(color="#94A3B8", size=12),
    ),
)
st.plotly_chart(fig_heat, use_container_width=True)

st.divider()

# ── Country drilldown ─────────────────────────────────────────────────────────
st.subheader("Country Drilldown")

country_options = grs_top[["country_iso3", "country_name"]].values.tolist()
country_labels  = {iso3: name for iso3, name in country_options}

selected_iso3 = st.selectbox(
    "Select country",
    options=[r[0] for r in country_options],
    format_func=lambda k: country_labels.get(k, k),
)

trend_df = query(conn, Q.GRS_COUNTRY_TREND, [selected_iso3])
wb_df    = query(conn, Q.WB_INDICATORS_COUNTRY, [selected_iso3])

if trend_df.empty:
    st.info(f"No GRS trend data for {country_labels.get(selected_iso3, selected_iso3)}.")
else:
    left_col, right_col = st.columns(2)

    with left_col:
        st.markdown(f"**GRS trend – {country_labels.get(selected_iso3, selected_iso3)}**")
        band, band_color = grs_band(trend_df["grs_score"].iloc[-1])
        st.markdown(
            f"Latest score: <span style='color:{band_color};font-size:1.4rem;font-weight:700'>"
            f"{trend_df['grs_score'].iloc[-1]:.1f}</span> &nbsp; "
            f"<span style='color:{band_color}'>{band}</span>",
            unsafe_allow_html=True,
        )
        fig_trend = go.Figure()
        fig_trend.add_hrect(y0=0, y1=15, fillcolor="rgba(34,197,94,0.08)", line_width=0)
        fig_trend.add_hrect(y0=15, y1=30, fillcolor="rgba(234,179,8,0.08)", line_width=0)
        fig_trend.add_hrect(y0=30, y1=50, fillcolor="rgba(249,115,22,0.08)", line_width=0)
        fig_trend.add_hrect(y0=50, y1=100, fillcolor="rgba(239,68,68,0.08)", line_width=0)
        fig_trend.add_trace(go.Scatter(
            x=trend_df["month_start"], y=trend_df["grs_score"],
            mode="lines+markers",
            line=dict(color="#DC2626", width=2.5),
            marker=dict(size=5, color="#DC2626"),
            name="GRS",
        ))
        for ref, label in [(15, "Low"), (30, "Moderate"), (50, "Elevated")]:
            fig_trend.add_hline(y=ref, line_dash="dot", line_color="#475569",
                                annotation_text=label, annotation_font_color="#64748B")
        fig_trend.update_layout(
            height=300,
            paper_bgcolor="#0F172A", plot_bgcolor="#1E293B",
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(gridcolor="#334155"),
            yaxis=dict(gridcolor="#334155", range=[0, max(100, trend_df["grs_score"].max() + 5)]),
            showlegend=False,
        )
        st.plotly_chart(fig_trend, use_container_width=True)

    with right_col:
        st.markdown("**Driver contributions over time**")
        driver_colors = {
            "Conflict (incidents)":  "#EF4444",
            "Conflict (fatalities)": "#B91C1C",
            "Sanctions":             "#F97316",
            "Militarization":        "#8B5CF6",
            "News tension":          "#3B82F6",
        }

        fig_stack = go.Figure()
        for col, label in DRIVER_LABELS.items():
            weight = DRIVER_WEIGHTS[col]
            fig_stack.add_trace(go.Bar(
                x=trend_df["month_start"],
                y=(trend_df[col] * weight * 100).round(2),
                name=label,
                marker_color=driver_colors.get(label, "#6B7280"),
                hovertemplate=f"{label}: %{{y:.1f}}<extra></extra>",
            ))
        fig_stack.update_layout(
            barmode="stack",
            height=300,
            paper_bgcolor="#0F172A", plot_bgcolor="#1E293B",
            legend=dict(font=dict(color="#94A3B8", size=10), bgcolor="#1E293B",
                        orientation="h", yanchor="bottom", y=1.02),
            margin=dict(l=0, r=0, t=40, b=0),
            xaxis=dict(gridcolor="#334155"),
            yaxis=dict(gridcolor="#334155", title="GRS contribution"),
        )
        st.plotly_chart(fig_stack, use_container_width=True)

    # World Bank indicators for this country
    if not wb_df.empty:
        st.markdown("**World Bank indicators**")
        wb_pivot = wb_df.pivot_table(
            index="period_start", columns="indicator_name", values="value"
        ).reset_index()
        st.dataframe(wb_pivot, hide_index=True, use_container_width=True)
