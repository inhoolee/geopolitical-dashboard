-- Dimension tables for the geopolitical dashboard star schema

CREATE TABLE IF NOT EXISTS dim_region (
    region_code VARCHAR PRIMARY KEY,
    region_name VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_country (
    iso3        VARCHAR PRIMARY KEY,
    iso2        VARCHAR,
    name        VARCHAR NOT NULL,
    region_code VARCHAR REFERENCES dim_region(region_code)
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_key    DATE PRIMARY KEY,
    year        INTEGER NOT NULL,
    month       INTEGER NOT NULL,
    quarter     INTEGER NOT NULL,
    week_iso    INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,  -- 0 = Monday
    is_weekend  BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_event_type (
    event_type_code VARCHAR PRIMARY KEY,
    label           VARCHAR NOT NULL,
    source_system   VARCHAR,
    parent_type     VARCHAR
);

CREATE TABLE IF NOT EXISTS dim_source_system (
    source_system_code VARCHAR PRIMARY KEY,
    display_name       VARCHAR NOT NULL,
    url                VARCHAR,
    access_method      VARCHAR,  -- 'API' | 'Download' | 'Manual'
    coverage_start     DATE,
    coverage_end       DATE,     -- NULL = ongoing
    notes              VARCHAR
);

-- Pipeline state table for incremental runs
CREATE TABLE IF NOT EXISTS _pipeline_state (
    source_name              VARCHAR PRIMARY KEY,
    last_run_utc             TIMESTAMP,
    last_event_date_ingested DATE,
    records_processed        BIGINT,
    status                   VARCHAR   -- 'success' | 'partial' | 'failed'
);
