-- Fact tables for the geopolitical dashboard

CREATE TABLE IF NOT EXISTS fact_incident (
    incident_id          VARCHAR PRIMARY KEY,
    source_system        VARCHAR NOT NULL,
    source_event_id      VARCHAR,
    event_date           DATE    NOT NULL,
    event_date_end       DATE,
    country_iso3         VARCHAR,
    region_code          VARCHAR,
    admin1               VARCHAR,
    admin2               VARCHAR,
    location_name        VARCHAR,
    latitude             DOUBLE,
    longitude            DOUBLE,
    geo_precision        INTEGER,
    event_type           VARCHAR,
    sub_event_type       VARCHAR,
    disorder_type        VARCHAR,
    actor1_name          VARCHAR,
    actor2_name          VARCHAR,
    interaction_code     VARCHAR,
    civilian_targeting   BOOLEAN,
    event_count          INTEGER NOT NULL DEFAULT 1,
    fatalities_best      INTEGER,
    fatalities_low       INTEGER,
    fatalities_high      INTEGER,
    notes                VARCHAR,
    source_urls          VARCHAR,
    ingested_at_utc      TIMESTAMP NOT NULL DEFAULT current_timestamp
);

ALTER TABLE fact_incident ADD COLUMN IF NOT EXISTS event_count INTEGER DEFAULT 1;
UPDATE fact_incident SET event_count = 1 WHERE event_count IS NULL;

CREATE TABLE IF NOT EXISTS fact_diplomatic_action (
    action_id            VARCHAR PRIMARY KEY,
    action_date          DATE,
    actor_iso3           VARCHAR,
    target_iso3          VARCHAR,
    action_type          VARCHAR,
    action_subtype       VARCHAR,
    instrument_name      VARCHAR,
    legal_basis          VARCHAR,
    status               VARCHAR,  -- active | expired | reversed | completed
    confidence_flag      VARCHAR DEFAULT 'HIGH',  -- LOW when date is inferred
    source_url           VARCHAR,
    region               VARCHAR,
    notes                VARCHAR,
    ingested_at_utc      TIMESTAMP NOT NULL DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS fact_risk_indicator (
    country_iso3         VARCHAR NOT NULL,
    period_start         DATE    NOT NULL,
    indicator_code       VARCHAR NOT NULL,
    indicator_name       VARCHAR,
    value                DOUBLE,
    unit                 VARCHAR,
    source_system        VARCHAR,
    source_url           VARCHAR,
    ingested_at_utc      TIMESTAMP NOT NULL DEFAULT current_timestamp,
    PRIMARY KEY (country_iso3, period_start, indicator_code)
);

CREATE TABLE IF NOT EXISTS fact_news_pulse (
    item_id              VARCHAR PRIMARY KEY,
    published_at_utc     TIMESTAMP,
    country_focus_iso3   VARCHAR,
    region_code          VARCHAR,
    title                VARCHAR,
    source_domain        VARCHAR,
    url                  VARCHAR,
    topic_tags           VARCHAR,
    attention_count      INTEGER DEFAULT 1,
    tone                 DOUBLE,
    ingested_at_utc      TIMESTAMP NOT NULL DEFAULT current_timestamp
);
