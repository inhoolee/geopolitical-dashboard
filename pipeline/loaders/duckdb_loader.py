"""Generic DuckDB loader with idempotent upsert semantics."""

import logging
from datetime import datetime, timezone

import duckdb
import pandas as pd

logger = logging.getLogger(__name__)

# Map of table name → primary key column(s)
TABLE_PK: dict[str, list[str]] = {
    "fact_incident": ["incident_id"],
    "fact_diplomatic_action": ["action_id"],
    "fact_news_pulse": ["item_id"],
    "fact_risk_indicator": ["country_iso3", "period_start", "indicator_code"],
    "dim_country": ["iso3"],
    "dim_region": ["region_code"],
    "dim_event_type": ["event_type_code"],
    "dim_source_system": ["source_system_code"],
    "dim_date": ["date_key"],
}


def upsert(
    conn: duckdb.DuckDBPyConnection,
    table: str,
    df: pd.DataFrame,
    add_ingested_at: bool = True,
) -> int:
    """
    Insert or replace rows into a DuckDB table from a DataFrame.
    Returns the number of rows written.
    """
    if df.empty:
        logger.info("Loader: nothing to write for %s (empty DataFrame)", table)
        return 0

    if add_ingested_at and "ingested_at_utc" not in df.columns:
        df = df.copy()
        df["ingested_at_utc"] = datetime.now(timezone.utc)

    # Register the DataFrame as a temporary view
    conn.register("_staging", df)

    # Get target table columns to avoid inserting unknown fields
    target_cols = [
        row[0]
        for row in conn.execute(
            f"SELECT column_name FROM information_schema.columns "
            f"WHERE table_name = '{table}' ORDER BY ordinal_position"
        ).fetchall()
    ]

    # Keep only columns that exist in both source and target
    common_cols = [c for c in target_cols if c in df.columns]
    col_list = ", ".join(common_cols)

    # INSERT OR REPLACE is the simplest idempotent strategy in DuckDB;
    # it deletes any conflicting row then inserts fresh, which is correct for our use case.
    sql = f"INSERT OR REPLACE INTO {table} ({col_list}) SELECT {col_list} FROM _staging"

    conn.execute(sql)
    conn.commit()
    n = len(df)
    logger.info("Loaded %d rows into %s", n, table)
    return n


def update_pipeline_state(
    conn: duckdb.DuckDBPyConnection,
    source_name: str,
    records_processed: int,
    last_event_date=None,
    status: str = "success",
) -> None:
    """Update the _pipeline_state tracking table."""
    now = datetime.now(timezone.utc)
    conn.execute(
        """
        INSERT INTO _pipeline_state (source_name, last_run_utc, last_event_date_ingested,
                                     records_processed, status)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (source_name) DO UPDATE SET
            last_run_utc             = EXCLUDED.last_run_utc,
            last_event_date_ingested = EXCLUDED.last_event_date_ingested,
            records_processed        = EXCLUDED.records_processed,
            status                   = EXCLUDED.status
        """,
        [source_name, now, last_event_date, records_processed, status],
    )
    conn.commit()
