"""All SQL queries as named module-level constants."""

# ---------------------------------------------------------------------------
# Shared / sidebar
# ---------------------------------------------------------------------------

PIPELINE_STATE = """
SELECT source_name,
       STRFTIME(last_run_utc, '%Y-%m-%d %H:%M') AS last_run,
       records_processed,
       status
FROM _pipeline_state
ORDER BY last_run_utc DESC
"""

# ---------------------------------------------------------------------------
# Page 1 – Overview
# ---------------------------------------------------------------------------

KPI_GLOBAL = """
SELECT
    SUM(event_count)                                            AS total_incidents,
    SUM(fatalities_best)                                        AS total_fatalities,
    COUNT(DISTINCT country_iso3)                                AS countries_affected,
    SUM(CASE WHEN civilian_targeting THEN event_count ELSE 0 END) AS civilian_incidents
FROM fact_incident
WHERE event_date BETWEEN ?::DATE AND ?::DATE
"""

# Latest non-null GRS per country
CHOROPLETH_GRS = """
SELECT g.country_iso3,
       COALESCE(dc.name, g.country_iso3) AS country_name,
       ROUND(g.grs_0_100, 1)             AS grs_score,
       g.month_start                     AS score_month,
       g.coverage_flag
FROM grs_monthly g
JOIN (
    SELECT country_iso3, MAX(month_start) AS latest_month
    FROM grs_monthly
    WHERE grs_0_100 IS NOT NULL
    GROUP BY country_iso3
) lm ON g.country_iso3 = lm.country_iso3
     AND g.month_start  = lm.latest_month
LEFT JOIN dim_country dc ON dc.iso3 = g.country_iso3
ORDER BY g.grs_0_100 DESC NULLS LAST
"""

TOP_MOVERS = """
WITH scored AS (
    SELECT country_iso3, month_start, grs_0_100
    FROM grs_monthly
    WHERE grs_0_100 IS NOT NULL
),
paired AS (
    SELECT a.country_iso3,
           b.grs_0_100 - a.grs_0_100  AS delta,
           b.grs_0_100                 AS current_grs,
           b.month_start               AS current_month
    FROM scored a
    JOIN scored b
      ON a.country_iso3 = b.country_iso3
     AND b.month_start  = a.month_start + INTERVAL 1 MONTH
),
latest AS (
    SELECT country_iso3, delta, current_grs, current_month,
           ROW_NUMBER() OVER (PARTITION BY country_iso3 ORDER BY current_month DESC) AS rn
    FROM paired
)
SELECT l.country_iso3,
       COALESCE(dc.name, l.country_iso3) AS country,
       ROUND(l.current_grs, 1)           AS grs,
       ROUND(l.delta, 1)                 AS delta
FROM latest l
LEFT JOIN dim_country dc ON dc.iso3 = l.country_iso3
WHERE rn = 1
ORDER BY ABS(l.delta) DESC
LIMIT 12
"""

DIPLOMATIC_FEED = """
SELECT action_date,
       COALESCE(actor_iso3, '') AS actor,
       COALESCE(target_iso3, '') AS target,
       action_type,
       instrument_name,
       status
FROM fact_diplomatic_action
WHERE action_type != 'sanction'
  AND action_date IS NOT NULL
ORDER BY action_date DESC
LIMIT 15
"""

TOP10_RISK = """
SELECT g.country_iso3,
       COALESCE(dc.name, g.country_iso3) AS country,
       ROUND(g.grs_0_100, 1)             AS grs_score,
       g.coverage_flag,
       g.month_start                     AS as_of
FROM grs_monthly g
JOIN (
    SELECT country_iso3, MAX(month_start) AS m
    FROM grs_monthly WHERE grs_0_100 IS NOT NULL GROUP BY country_iso3
) lm ON g.country_iso3 = lm.country_iso3 AND g.month_start = lm.m
LEFT JOIN dim_country dc ON dc.iso3 = g.country_iso3
ORDER BY g.grs_0_100 DESC NULLS LAST
LIMIT 10
"""

# ---------------------------------------------------------------------------
# Page 2 – Incidents
# ---------------------------------------------------------------------------

WEEKLY_TIMELINE = """
SELECT week_start,
       SUM(incident_count)    AS incidents,
       SUM(fatalities_total)  AS fatalities,
       SUM(civilian_incidents) AS civilian_incidents
FROM country_week_agg
WHERE week_start BETWEEN ?::DATE AND ?::DATE
GROUP BY week_start
ORDER BY week_start
"""

WEEKLY_TIMELINE_REGION = """
SELECT week_start,
       SUM(incident_count)    AS incidents,
       SUM(fatalities_total)  AS fatalities,
       SUM(civilian_incidents) AS civilian_incidents
FROM country_week_agg
WHERE week_start BETWEEN ?::DATE AND ?::DATE
  AND region_code = ?
GROUP BY week_start
ORDER BY week_start
"""

REGION_BREAKDOWN = """
SELECT COALESCE(region_code, 'Unknown') AS region,
       SUM(incident_count)    AS incidents,
       SUM(fatalities_total)  AS fatalities
FROM country_month_agg
WHERE month_start BETWEEN DATE_TRUNC('month', ?::DATE)
                      AND DATE_TRUNC('month', ?::DATE)
GROUP BY region
ORDER BY incidents DESC
"""

EVENT_TYPE_BREAKDOWN = """
SELECT event_type,
       SUM(event_count)     AS incident_count,
       SUM(fatalities_best) AS fatalities
FROM fact_incident
WHERE event_date BETWEEN ?::DATE AND ?::DATE
  AND event_type IS NOT NULL
GROUP BY event_type
ORDER BY incident_count DESC
"""

TOP_FATALITIES = """
SELECT fi.country_iso3,
       COALESCE(dc.name, fi.country_iso3) AS country,
       SUM(fi.fatalities_best)            AS total_fatalities,
       SUM(fi.event_count)                AS total_incidents
FROM fact_incident fi
LEFT JOIN dim_country dc ON dc.iso3 = fi.country_iso3
WHERE fi.event_date BETWEEN ?::DATE AND ?::DATE
GROUP BY fi.country_iso3, dc.name
ORDER BY total_fatalities DESC NULLS LAST
LIMIT 20
"""

# ---------------------------------------------------------------------------
# Page 3 – Diplomatic Actions
# ---------------------------------------------------------------------------

SANCTIONS_BY_COUNTRY = """
SELECT COALESCE(target_iso3, 'Unknown') AS target,
       COALESCE(dc.name, target_iso3)   AS country_name,
       COUNT(*)                         AS total_sanctions,
       COUNT(*) FILTER (WHERE status = 'active') AS active_sanctions
FROM fact_diplomatic_action da
LEFT JOIN dim_country dc ON dc.iso3 = da.target_iso3
WHERE action_type = 'sanction'
  AND target_iso3 IS NOT NULL
GROUP BY da.target_iso3, dc.name
ORDER BY total_sanctions DESC
LIMIT 20
"""

SEED_EVENTS_TIMELINE = """
SELECT action_date,
       COALESCE(actor_iso3, '') AS actor_iso3,
       COALESCE(target_iso3, '') AS target_iso3,
       action_type,
       action_subtype,
       instrument_name,
       status,
       region,
       notes,
       source_url
FROM fact_diplomatic_action
WHERE action_type != 'sanction'
  AND action_date IS NOT NULL
ORDER BY action_date
"""

ACTIONS_BY_TYPE = """
SELECT action_type,
       COUNT(*) AS count
FROM fact_diplomatic_action
WHERE action_type != 'sanction'
GROUP BY action_type
ORDER BY count DESC
"""

# ---------------------------------------------------------------------------
# Page 4 – Risk Score
# ---------------------------------------------------------------------------

GRS_HEATMAP = """
SELECT g.country_iso3,
       COALESCE(dc.name, g.country_iso3) AS country_name,
       ROUND(g.score_inc_norm, 3)    AS conflict_incidents,
       ROUND(g.score_fat_norm, 3)    AS conflict_fatalities,
       ROUND(g.score_san_norm, 3)    AS sanctions,
       ROUND(g.score_mil_norm, 3)    AS militarization,
       ROUND(g.score_news_norm, 3)   AS news_tension,
       ROUND(g.grs_0_100, 1)         AS grs_score,
       g.coverage_flag
FROM grs_monthly g
JOIN (
    SELECT country_iso3, MAX(month_start) AS m
    FROM grs_monthly WHERE grs_0_100 IS NOT NULL GROUP BY country_iso3
) lm ON g.country_iso3 = lm.country_iso3 AND g.month_start = lm.m
LEFT JOIN dim_country dc ON dc.iso3 = g.country_iso3
WHERE g.grs_0_100 IS NOT NULL
ORDER BY g.grs_0_100 DESC NULLS LAST
LIMIT 40
"""

GRS_COUNTRY_TREND = """
SELECT month_start,
       ROUND(grs_0_100, 1)       AS grs_score,
       ROUND(score_inc_norm, 3)  AS conflict_incidents,
       ROUND(score_fat_norm, 3)  AS conflict_fatalities,
       ROUND(score_san_norm, 3)  AS sanctions,
       ROUND(score_mil_norm, 3)  AS militarization,
       ROUND(score_news_norm, 3) AS news_tension
FROM grs_monthly
WHERE country_iso3 = ?
  AND grs_0_100 IS NOT NULL
ORDER BY month_start
"""

WB_INDICATORS_COUNTRY = """
SELECT period_start,
       indicator_name,
       ROUND(value, 2) AS value,
       unit
FROM fact_risk_indicator
WHERE country_iso3 = ?
ORDER BY indicator_name, period_start
"""
