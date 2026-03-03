# Geopolitical Dashboard ETL

ETL pipeline and DuckDB warehouse for tracking geopolitical change from **2017-01-20 onward** (Trump first inauguration boundary), built to feed a Tableau dashboard.

## What This Repo Does

- Extracts raw data from:
  - ACLED (conflict events, optional credentials)
  - UCDP GED v25.1 (conflict events, historical baseline)
  - World Bank WDI (macro + military spend indicators)
  - OFAC SDN (sanctions actions)
  - GDELT DOC 2.0 (news attention/tension proxy)
  - Seeded diplomatic event catalog (`data/seeds/diplomatic_events_seed.csv`)
- Transforms all sources into a canonical star-like model.
- Loads into DuckDB with idempotent upsert behavior.
- Builds aggregate views for dashboard performance.
- Includes SQL for a composite Geopolitical Risk Score (`grs_monthly`) and QA checks.

## Repository Layout

```text
docs/
  domain-information.md      # domain scope, entities, source coverage, caveats

pipeline/
  config.py                  # env vars, paths, source URLs, indicator codes
  db.py                      # DuckDB connection + schema bootstrap
  extractors/                # raw pulls into data/raw/<source>/
  transformers/              # source -> canonical DataFrames
  loaders/duckdb_loader.py   # upsert + _pipeline_state updates

scripts/
  bootstrap_db.py            # create schema + seed dim_region/dim_source_system
  seed_dimensions.py         # seed dim_country/dim_date/dim_event_type
  run_pipeline.py            # orchestrate extract -> transform -> load

sql/
  schema/                    # base tables + aggregate views
  queries/risk_score.sql     # creates grs_monthly view
  queries/validation.sql     # data quality checks
```

## Documentation

- Domain overview: `docs/domain-information.md`

## Prerequisites

- Python 3.10+
- `uv` (Python package/dependency manager)
- Network access for external data pulls
- Optional ACLED credentials for post-2024 incident coverage

Install dependencies:

```bash
uv sync --dev
```

## Environment Configuration

Create `.env` from the template:

```bash
cp .env.example .env
```

`.env.example` supports:

- `ACLED_API_KEY` + `ACLED_EMAIL` (optional but strongly recommended)
- `WAREHOUSE_PATH` (optional override of `data/warehouse/geopolitical.duckdb`)

## Quickstart

1. Initialize schema + static dimensions:

```bash
uv run python scripts/bootstrap_db.py
uv run python scripts/seed_dimensions.py
```

2. Run a small local-only load (seed events only):

```bash
uv run python scripts/run_pipeline.py --sources seed
```

3. Run all available sources:

```bash
uv run python scripts/run_pipeline.py --sources all
```

4. Force re-download of raw inputs:

```bash
uv run python scripts/run_pipeline.py --sources all --full-refresh
```

## Source Selection

`uv run python scripts/run_pipeline.py --sources ...` accepts:

- `all`
- `ucdp`
- `acled`
- `wb`
- `ofac`
- `seed`
- `gdelt`

Examples:

```bash
uv run python scripts/run_pipeline.py --sources wb,ofac,seed
uv run python scripts/run_pipeline.py --sources acled --log-level DEBUG
```

## Data Model

Core fact tables:

- `fact_incident`
- `fact_diplomatic_action`
- `fact_risk_indicator`
- `fact_news_pulse`

Core dimensions:

- `dim_country`
- `dim_region`
- `dim_date`
- `dim_event_type`
- `dim_source_system`

Pipeline bookkeeping:

- `_pipeline_state` (last run status by source)

Pre-aggregated dashboard views are created during schema bootstrap:

- `country_week_agg`
- `country_month_agg`
- `country_year_diplomatic`
- `country_week_news`

## Run Analytical SQL

Create/update `grs_monthly`:

```bash
uv run python - <<'PY'
from pathlib import Path
from pipeline.db import get_connection
conn = get_connection()
conn.execute(Path("sql/queries/risk_score.sql").read_text())
print("Created/updated view: grs_monthly")
PY
```

Run validation checks:

```bash
uv run python - <<'PY'
from pathlib import Path
from pipeline.db import get_connection
conn = get_connection()
sql_text = Path("sql/queries/validation.sql").read_text()
statements = [s.strip() for s in sql_text.split(";") if s.strip()]
for stmt in statements:
    rows = conn.execute(stmt).fetchall()
    if rows:
        print(rows[0][0], rows[0][1])
PY
```

## Known Data Caveats

- UCDP GED in this pipeline is v25.1 and ends at **2024-12-31**.
- ACLED is optional in code, but required for reliable post-2024 incident coverage.
- OFAC SDN CSV has no canonical designation date in this implementation; `action_date` is ingestion-date based and flagged `LOW` confidence.
- GDELT extraction is batched in ~90-day windows and capped by `GDELT_MAX_RECORDS` per query window.

## Troubleshooting

- DuckDB lock error (`Could not set lock on file ...`):
  - Another process is connected to the same warehouse file.
  - Stop the other process or run with a different `WAREHOUSE_PATH`.

- ACLED silently skipped:
  - Confirm both `ACLED_API_KEY` and `ACLED_EMAIL` are set in `.env`.

- No rows loaded for a source:
  - Check `data/raw/<source>/` files exist.
  - Re-run with `--full-refresh` and `--log-level DEBUG`.

## Current Status Snapshot

The seed-only path is validated in this repo:

- Schema bootstrap: success
- Dimension seeding: success (`dim_country` 253 rows, `dim_date` 7670 rows)
- Seed events load: success (41 rows into `fact_diplomatic_action`)
