-- QA validation checks – run after each pipeline load

-- 1. Duplicate incident IDs (should return 0 rows)
SELECT 'fact_incident duplicate PKs' AS check_name, COUNT(*) AS violations
FROM (SELECT incident_id FROM fact_incident GROUP BY incident_id HAVING COUNT(*) > 1);

-- 2. Incidents with invalid lat/lon
SELECT 'fact_incident invalid lat/lon' AS check_name, COUNT(*) AS violations
FROM fact_incident
WHERE latitude IS NOT NULL AND (latitude < -90 OR latitude > 90)
   OR longitude IS NOT NULL AND (longitude < -180 OR longitude > 180);

-- 3. Incidents with negative fatalities
SELECT 'fact_incident negative fatalities' AS check_name, COUNT(*) AS violations
FROM fact_incident
WHERE fatalities_best < 0 OR fatalities_low < 0 OR fatalities_high < 0;

-- 4. Duplicate diplomatic action IDs
SELECT 'fact_diplomatic_action duplicate PKs' AS check_name, COUNT(*) AS violations
FROM (SELECT action_id FROM fact_diplomatic_action GROUP BY action_id HAVING COUNT(*) > 1);

-- 5. Risk indicator: missing country mapping
SELECT 'fact_risk_indicator unmapped countries' AS check_name, COUNT(DISTINCT country_iso3) AS violations
FROM fact_risk_indicator
WHERE country_iso3 NOT IN (SELECT iso3 FROM dim_country);

-- 6. Incident coverage gap: no ACLED records after UCDP coverage ends
SELECT 'post-2024 incident coverage (ACLED only)' AS check_name,
       COUNT(*) AS total_events,
       COUNT(*) FILTER (WHERE source_system = 'ACLED') AS acled_events
FROM fact_incident
WHERE event_date > '2024-12-31';

-- 7. News pulse articles without country focus
SELECT 'fact_news_pulse missing country' AS check_name, COUNT(*) AS violations
FROM fact_news_pulse
WHERE country_focus_iso3 IS NULL;
