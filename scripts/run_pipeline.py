"""Main ETL orchestrator.

Usage:
    uv run python scripts/run_pipeline.py [--sources all|ucdp|wb|ofac|seed|gdelt|acled] [--full-refresh]

Example:
    uv run python scripts/run_pipeline.py                        # incremental, all available sources
    uv run python scripts/run_pipeline.py --sources seed,wb      # seed events + World Bank only
    uv run python scripts/run_pipeline.py --full-refresh         # re-download everything
"""

import argparse
import logging
import sys
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
) -> int:
    """Extract → transform → load one source. Returns rows loaded."""
    logger.info("=== %s ===", name)
    ok = extractor.run(force=force)
    if not ok:
        logger.warning("%s skipped (extractor unavailable)", name)
        return 0
    try:
        df = transform_fn()
        if df.empty:
            logger.warning("%s: transformer returned empty DataFrame", name)
            update_pipeline_state(conn, name, 0, status="partial")
            return 0
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

    conn = get_connection()
    bootstrap_schema(conn)

    total_rows = 0
    for key in source_keys:
        extractor, transform_fn, table = SOURCES[key]
        total_rows += run_source(
            name=key.upper(),
            extractor=extractor,
            transform_fn=transform_fn,
            table=table,
            conn=conn,
            force=args.full_refresh,
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
