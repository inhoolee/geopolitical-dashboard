"""Main ETL orchestrator.

Usage:
    uv run python scripts/run_pipeline.py [--sources all|ucdp|wb|ofac|seed|gdelt|acled]
                                      [--full-refresh]
                                      [--gdelt-start-date YYYY-MM-DD]
                                      [--gdelt-end-date YYYY-MM-DD]

Example:
    uv run python scripts/run_pipeline.py                        # incremental, all available sources
    uv run python scripts/run_pipeline.py --sources seed,wb      # seed events + World Bank only
    uv run python scripts/run_pipeline.py --full-refresh         # re-download everything
    uv run python scripts/run_pipeline.py --sources gdelt --gdelt-start-date 2020-01-01
"""

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.db import get_connection, bootstrap_schema
from pipeline.utils.logging_config import setup_logging
from pipeline.loaders.duckdb_loader import upsert, update_pipeline_state

# Extractors
from pipeline.extractors.ucdp_ged import UCDPGEDExtractor
from pipeline.extractors.world_bank import WorldBankExtractor
from pipeline.extractors.ofac_sdn import OFACSDNExtractor
from pipeline.extractors.seed_events import SeedEventsExtractor
from pipeline.extractors.gdelt import GDELTExtractor
from pipeline.extractors.acled import ACLEDExtractor

# Transformers
from pipeline.transformers import ucdp_ged as t_ucdp
from pipeline.transformers import world_bank as t_wb
from pipeline.transformers import ofac_sdn as t_ofac
from pipeline.transformers import seed_events as t_seed
from pipeline.transformers import gdelt as t_gdelt
from pipeline.transformers import acled as t_acled

logger = logging.getLogger(__name__)


def run_source(
    name: str,
    extractor,
    transform_fn,
    table: str,
    conn,
    force: bool,
    replace_source_system: str | None = None,
    extract_kwargs: dict | None = None,
) -> int:
    """Extract → transform → load one source. Returns rows loaded."""
    logger.info("=== %s ===", name)
    ok = extractor.run(force=force, **(extract_kwargs or {}))
    if not ok:
        logger.warning("%s skipped (extractor unavailable)", name)
        return 0
    try:
        df = transform_fn()
        if df.empty:
            logger.warning("%s: transformer returned empty DataFrame", name)
            update_pipeline_state(conn, name, 0, status="partial")
            return 0
        if replace_source_system:
            try:
                conn.execute("BEGIN")
                conn.execute(
                    f"DELETE FROM {table} WHERE source_system = ?",
                    [replace_source_system],
                )
                n = upsert(conn, table, df, commit=False)
                conn.execute("COMMIT")
                logger.info("%s load mode: full replace for source_system=%s", name, replace_source_system)
            except Exception:
                conn.execute("ROLLBACK")
                raise
        else:
            n = upsert(conn, table, df)
        last_date = None
        if "event_date" in df.columns:
            last_date = df["event_date"].max()
        elif "action_date" in df.columns:
            last_date = df["action_date"].max()
        elif "period_start" in df.columns:
            last_date = df["period_start"].max()
        update_pipeline_state(conn, name, n, last_date, "success")
        return n
    except Exception as exc:
        logger.exception("%s transform/load failed: %s", name, exc)
        update_pipeline_state(conn, name, 0, status="failed")
        return 0


SOURCES = {
    "ucdp": (UCDPGEDExtractor(), t_ucdp.transform, "fact_incident"),
    "acled": (ACLEDExtractor(), t_acled.transform, "fact_incident"),
    "wb": (WorldBankExtractor(), t_wb.transform, "fact_risk_indicator"),
    "ofac": (OFACSDNExtractor(), t_ofac.transform, "fact_diplomatic_action"),
    "seed": (SeedEventsExtractor(), t_seed.transform, "fact_diplomatic_action"),
    "gdelt": (GDELTExtractor(), t_gdelt.transform, "fact_news_pulse"),
}


def parse_iso_date(value: str) -> date:
    """argparse type parser for YYYY-MM-DD dates."""
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid date '{value}'. Expected format: YYYY-MM-DD"
        ) from exc


def validate_gdelt_date_args(
    source_keys: list[str],
    gdelt_start_date: date | None,
    gdelt_end_date: date | None,
    today: date | None = None,
) -> tuple[date | None, date | None]:
    """Validate and normalize GDELT date arguments."""
    if gdelt_start_date is None and gdelt_end_date is None:
        return None, None

    if "gdelt" not in source_keys:
        raise ValueError("GDELT date arguments require --sources to include 'gdelt'")

    if gdelt_start_date is None and gdelt_end_date is not None:
        raise ValueError("--gdelt-end-date requires --gdelt-start-date")

    if gdelt_start_date is not None and gdelt_end_date is None:
        gdelt_end_date = today or date.today()

    if gdelt_start_date and gdelt_end_date and gdelt_start_date > gdelt_end_date:
        raise ValueError("--gdelt-start-date cannot be after --gdelt-end-date")

    return gdelt_start_date, gdelt_end_date


def main() -> None:
    parser = argparse.ArgumentParser(description="Geopolitical dashboard ETL pipeline")
    parser.add_argument(
        "--sources",
        default="all",
        help="Comma-separated source keys: all|ucdp|wb|ofac|seed|gdelt|acled",
    )
    parser.add_argument(
        "--full-refresh",
        action="store_true",
        help="Force re-download of all raw data",
    )
    parser.add_argument(
        "--gdelt-start-date",
        type=parse_iso_date,
        help="GDELT start date (YYYY-MM-DD). If set without --gdelt-end-date, end date defaults to today.",
    )
    parser.add_argument(
        "--gdelt-end-date",
        type=parse_iso_date,
        help="GDELT end date (YYYY-MM-DD). Requires --gdelt-start-date.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    args = parser.parse_args()

    setup_logging(getattr(logging, args.log_level))

    source_keys = list(SOURCES.keys()) if args.sources == "all" else [
        s.strip() for s in args.sources.split(",")
    ]
    invalid = [k for k in source_keys if k not in SOURCES]
    if invalid:
        logger.error("Unknown source keys: %s. Valid: %s", invalid, list(SOURCES.keys()))
        sys.exit(1)
    try:
        gdelt_start_date, gdelt_end_date = validate_gdelt_date_args(
            source_keys=source_keys,
            gdelt_start_date=args.gdelt_start_date,
            gdelt_end_date=args.gdelt_end_date,
        )
    except ValueError as exc:
        parser.error(str(exc))

    conn = get_connection()
    bootstrap_schema(conn)

    total_rows = 0
    for key in source_keys:
        extractor, transform_fn, table = SOURCES[key]
        extract_kwargs = None
        if key == "gdelt":
            extract_kwargs = {
                "start_date": gdelt_start_date,
                "end_date": gdelt_end_date,
            }
        total_rows += run_source(
            name=key.upper(),
            extractor=extractor,
            transform_fn=transform_fn,
            table=table,
            conn=conn,
            force=args.full_refresh,
            replace_source_system="ACLED" if key == "acled" else None,
            extract_kwargs=extract_kwargs,
        )

    logger.info("Pipeline complete. Total rows loaded: %d", total_rows)

    # Print quick summary
    for table in ["fact_incident", "fact_diplomatic_action", "fact_risk_indicator", "fact_news_pulse"]:
        try:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            logger.info("  %-30s %d rows", table, count)
        except Exception:
            pass


if __name__ == "__main__":
    main()
