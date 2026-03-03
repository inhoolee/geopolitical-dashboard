-- Pre-aggregated views for Tableau performance

CREATE OR REPLACE VIEW country_week_agg AS
SELECT
    date_trunc('week', fi.event_date)            AS week_start,
    fi.country_iso3,
    fi.region_code,
    fi.event_type,
    CAST(SUM(COALESCE(fi.event_count, 1)) AS BIGINT) AS incident_count,
    CAST(SUM(fi.fatalities_best) AS BIGINT)      AS fatalities_total,
    CAST(
        SUM(CASE WHEN fi.civilian_targeting THEN COALESCE(fi.event_count, 1) ELSE 0 END)
        AS BIGINT
    )                                            AS civilian_incidents,
    COUNT(DISTINCT fi.source_system)             AS source_count
FROM fact_incident fi
GROUP BY 1, 2, 3, 4;

CREATE OR REPLACE VIEW country_month_agg AS
SELECT
    date_trunc('month', fi.event_date)           AS month_start,
    fi.country_iso3,
    fi.region_code,
    CAST(SUM(COALESCE(fi.event_count, 1)) AS BIGINT) AS incident_count,
    CAST(SUM(fi.fatalities_best) AS BIGINT)      AS fatalities_total,
    CAST(
        SUM(CASE WHEN fi.civilian_targeting THEN COALESCE(fi.event_count, 1) ELSE 0 END)
        AS BIGINT
    )                                            AS civilian_incidents
FROM fact_incident fi
GROUP BY 1, 2, 3;

-- Diplomatic action summary by country-year
CREATE OR REPLACE VIEW country_year_diplomatic AS
SELECT
    date_trunc('year', da.action_date)           AS year_start,
    COALESCE(da.target_iso3, da.actor_iso3)      AS country_iso3,
    da.action_type,
    COUNT(*)                                     AS action_count
FROM fact_diplomatic_action da
WHERE da.action_date IS NOT NULL
GROUP BY 1, 2, 3;

-- News attention by country-week
CREATE OR REPLACE VIEW country_week_news AS
SELECT
    date_trunc('week', np.published_at_utc::DATE) AS week_start,
    np.country_focus_iso3,
    np.region_code,
    COUNT(*)                                      AS article_count,
    AVG(np.tone)                                  AS avg_tone
FROM fact_news_pulse np
WHERE np.country_focus_iso3 IS NOT NULL
GROUP BY 1, 2, 3;
