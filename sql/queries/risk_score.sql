-- Geopolitical Risk Score (GRS) computation
-- Weights (tunable via Tableau parameters; defaults shown):
--   Conflict & violence:        0.45
--   Diplomatic/economic coercion: 0.20
--   Militarization:             0.15
--   Governance/macro stress:    0.10
--   News-derived tension:       0.10

CREATE OR REPLACE VIEW grs_monthly AS
WITH

-- -----------------------------------------------------------------------
-- 1. Conflict component: incident rate + fatality rate (last 12 months)
-- -----------------------------------------------------------------------
pop AS (
    SELECT country_iso3, period_start, value AS population
    FROM fact_risk_indicator
    WHERE indicator_code = 'SP.POP.TOTL'
),
incidents_monthly AS (
    SELECT
        country_iso3,
        date_trunc('month', event_date) AS month_start,
        SUM(COALESCE(event_count, 1))   AS incident_count,
        SUM(fatalities_best)            AS fatalities
    FROM fact_incident
    GROUP BY 1, 2
),
conflict_base AS (
    SELECT
        im.country_iso3,
        im.month_start,
        im.incident_count,
        im.fatalities,
        p.population,
        -- per-100k rates; NULL-safe via NULLIF
        -- ASOF JOIN: falls back to latest available WB year when exact year is missing (e.g. 2025 incidents use 2024 population)
        (im.incident_count  * 1e5 / NULLIF(p.population, 0)) AS incident_rate_100k,
        (im.fatalities      * 1e5 / NULLIF(p.population, 0)) AS fatality_rate_100k
    FROM incidents_monthly im
    ASOF LEFT JOIN pop p
           ON p.country_iso3 = im.country_iso3
          AND date_trunc('year', im.month_start) >= p.period_start
),

-- -----------------------------------------------------------------------
-- 2. Diplomatic/economic coercion: sanctions count (trailing 12 months)
-- -----------------------------------------------------------------------
sanctions_monthly AS (
    SELECT
        COALESCE(target_iso3, actor_iso3) AS country_iso3,
        date_trunc('month', action_date)  AS month_start,
        COUNT(*)                          AS sanction_count
    FROM fact_diplomatic_action
    WHERE action_type = 'sanction'
      AND action_date IS NOT NULL
    GROUP BY 1, 2
),

-- -----------------------------------------------------------------------
-- 3. Militarization: military expenditure % GDP (structural, annual)
-- -----------------------------------------------------------------------
milex AS (
    SELECT country_iso3, period_start, value AS milex_pct_gdp
    FROM fact_risk_indicator
    WHERE indicator_code = 'MS.MIL.XPND.GD.ZS'
),

-- -----------------------------------------------------------------------
-- 4. News tension: article volume and tone (trailing 30 days proxy)
-- -----------------------------------------------------------------------
news_monthly AS (
    SELECT
        country_focus_iso3              AS country_iso3,
        date_trunc('month', published_at_utc::DATE) AS month_start,
        COUNT(*)                        AS article_count,
        AVG(tone)                       AS avg_tone
    FROM fact_news_pulse
    WHERE country_focus_iso3 IS NOT NULL
    GROUP BY 1, 2
),

-- -----------------------------------------------------------------------
-- 5. Combine and normalize (min-max over entire dataset window)
-- -----------------------------------------------------------------------
combined AS (
    SELECT
        cb.country_iso3,
        cb.month_start,
        cb.incident_rate_100k,
        cb.fatality_rate_100k,
        COALESCE(sm.sanction_count, 0) AS sanction_count,
        mx.milex_pct_gdp,
        COALESCE(nm.article_count, 0)  AS article_count,
        nm.avg_tone
    FROM conflict_base cb
    LEFT JOIN sanctions_monthly sm USING (country_iso3, month_start)
    ASOF LEFT JOIN milex mx
           ON mx.country_iso3  = cb.country_iso3
          AND date_trunc('year', cb.month_start) >= mx.period_start
    LEFT JOIN news_monthly nm  USING (country_iso3, month_start)
),
norm_bounds AS (
    SELECT
        MAX(incident_rate_100k)  AS max_inc,  MIN(incident_rate_100k)  AS min_inc,
        MAX(fatality_rate_100k)  AS max_fat,  MIN(fatality_rate_100k)  AS min_fat,
        MAX(sanction_count)      AS max_san,  MIN(sanction_count)      AS min_san,
        MAX(milex_pct_gdp)       AS max_mil,  MIN(milex_pct_gdp)       AS min_mil,
        MAX(article_count)       AS max_art,  MIN(article_count)       AS min_art
    FROM combined
)

SELECT
    c.country_iso3,
    c.month_start,
    -- Normalized sub-scores (0–1)
    CASE WHEN b.max_inc > b.min_inc
         THEN (COALESCE(c.incident_rate_100k, 0) - b.min_inc) / (b.max_inc - b.min_inc)
         ELSE 0 END                                       AS score_inc_norm,
    CASE WHEN b.max_fat > b.min_fat
         THEN (COALESCE(c.fatality_rate_100k, 0) - b.min_fat) / (b.max_fat - b.min_fat)
         ELSE 0 END                                       AS score_fat_norm,
    CASE WHEN b.max_san > b.min_san
         THEN (c.sanction_count - b.min_san) / (b.max_san - b.min_san)
         ELSE 0 END                                       AS score_san_norm,
    CASE WHEN b.max_mil > b.min_mil
         THEN (c.milex_pct_gdp - b.min_mil) / (b.max_mil - b.min_mil)
         ELSE 0 END                                       AS score_mil_norm,
    CASE WHEN b.max_art > b.min_art
         THEN (c.article_count - b.min_art) / (b.max_art - b.min_art)
         ELSE 0 END                                       AS score_news_norm,
    -- GRS composite (weights: 0.45/0.225/0.225/0.20/0.15/0.10/0.10)
    100.0 * (
        0.45  * (
            0.5 * CASE WHEN b.max_inc > b.min_inc
                       THEN (COALESCE(c.incident_rate_100k, 0) - b.min_inc) / (b.max_inc - b.min_inc)
                       ELSE 0 END
          + 0.5 * CASE WHEN b.max_fat > b.min_fat
                       THEN (COALESCE(c.fatality_rate_100k, 0) - b.min_fat) / (b.max_fat - b.min_fat)
                       ELSE 0 END
        )
      + 0.20  * CASE WHEN b.max_san > b.min_san
                     THEN (c.sanction_count - b.min_san) / (b.max_san - b.min_san)
                     ELSE 0 END
      + 0.15  * COALESCE(
                    CASE WHEN b.max_mil > b.min_mil
                         THEN (c.milex_pct_gdp - b.min_mil) / (b.max_mil - b.min_mil)
                         ELSE 0 END, 0)
      + 0.10  * CASE WHEN b.max_art > b.min_art
                     THEN (c.article_count - b.min_art) / (b.max_art - b.min_art)
                     ELSE 0 END
      -- tone: lower (more negative) = higher tension; invert
      + 0.10  * CASE WHEN c.avg_tone IS NOT NULL
                     THEN GREATEST(0, LEAST(1, (-c.avg_tone + 10) / 20.0))
                     ELSE 0.5 END
    )                                                     AS grs_0_100,
    -- Data coverage flag
    CASE
        WHEN c.incident_rate_100k IS NULL AND c.article_count = 0 THEN 'NONE'
        WHEN c.milex_pct_gdp      IS NULL                         THEN 'PARTIAL'
        ELSE 'FULL'
    END                                                   AS coverage_flag
FROM combined c
CROSS JOIN norm_bounds b;
