# Domain Information

## Purpose

This project models **geopolitical change and risk** for a global dashboard.
The operational time boundary starts on **2017-01-20** and continues forward as new data arrives.

## Domain Scope

The pipeline covers four main analytical domains:

1. Conflict and security incidents
2. Diplomatic and sanctions actions
3. Structural macro and militarization indicators
4. News attention and tension signals

## Core Domain Model

Canonical dimensions:

- `dim_country`
- `dim_region`
- `dim_date`
- `dim_event_type`
- `dim_source_system`

Canonical fact tables:

- `fact_incident`
- `fact_diplomatic_action`
- `fact_risk_indicator`
- `fact_news_pulse`

## Primary Source Systems

- **ACLED**: weekly aggregated conflict/protest snapshots from local CSV files
- **UCDP GED v25.1**: structured conflict event baseline
- **World Bank WDI**: macro and military-related indicators
- **OFAC SDN**: sanctions-related actions
- **GDELT DOC 2.0**: headline/news attention proxy
- **Seeded diplomatic events**: curated starter event ledger

## Key Domain Metrics

- Incident volume and trend
- Fatalities and severity proxies
- Diplomatic action counts (for example sanctions and recognitions)
- Macro and militarization indicators (for example GDP per capita, military spend share)
- News volume/tone proxy
- Composite geopolitical risk outputs (for example `grs_monthly`)

## Temporal and Coverage Rules

- Coverage is designed to be **global** (no fixed country list).
- Events are tracked from **2017-01-20 onward**.
- UCDP GED coverage in this repo ends at **2024-12-31**; post-2024 conflict visibility depends on other enabled sources.

## Data Caveats

- ACLED in this repo is loaded from `data/raw/acled/*_aggregated_data_up_to-*.csv`.
- ACLED aggregate rows include `event_count`; trend metrics should use `SUM(event_count)`.
- OFAC designation timing in current implementation is ingestion-date based, not canonical designation-date based.
- News-based measures are directional proxies and should be interpreted with source and confidence context.
