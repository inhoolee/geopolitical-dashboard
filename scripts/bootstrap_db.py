"""Bootstrap the DuckDB warehouse schema and seed dimension tables."""

import logging
import sys
from pathlib import Path

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.db import get_connection, bootstrap_schema
from pipeline.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)

SOURCE_SYSTEM_SEED = [
    ("ACLED", "Armed Conflict Location and Event Data Project",
     "https://acleddata.com", "API", "2017-01-20", None,
     "API key required; register at https://acleddata.com/register/"),
    ("UCDP_GED", "UCDP Georeferenced Event Dataset v25.1",
     "https://ucdp.uu.se", "Download", "1989-01-01", "2024-12-31",
     "Annual release; 2025+ events require ACLED"),
    ("WORLD_BANK", "World Bank World Development Indicators",
     "https://api.worldbank.org", "API", "1960-01-01", None,
     "Free, no authentication required"),
    ("GDELT_DOC", "GDELT DOC 2.0 API",
     "https://api.gdeltproject.org", "API", "2017-01-01", None,
     "3-month API window; backfill batched by quarter"),
    ("OFAC_SDN", "OFAC Specially Designated Nationals List",
     "https://www.treasury.gov/ofac", "Download", None, None,
     "No original designation date in CSV; action_date is ingestion date"),
    ("SEED", "Curated event catalog from deep-research-report.md",
     None, "Manual", "2017-01-20", None,
     "Hand-maintained CSV; source of truth for major diplomatic milestones"),
]

REGION_SEED = [
    ("EU_EUR", "Europe and Eurasia"),
    ("MENA", "Middle East and North Africa"),
    ("SSA", "Sub-Saharan Africa"),
    ("SCA", "South and Central Asia"),
    ("EAP", "East Asia and Pacific"),
    ("AME", "Americas"),
    ("GLO", "Global / Multilateral"),
]


def main() -> None:
    setup_logging()
    logger.info("Bootstrapping database schema…")

    conn = get_connection()
    bootstrap_schema(conn)

    # Seed dim_region
    for row in REGION_SEED:
        conn.execute(
            "INSERT OR IGNORE INTO dim_region (region_code, region_name) VALUES (?, ?)", row
        )

    # Seed dim_source_system
    for row in SOURCE_SYSTEM_SEED:
        conn.execute(
            """INSERT OR IGNORE INTO dim_source_system
               (source_system_code, display_name, url, access_method,
                coverage_start, coverage_end, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            row,
        )

    conn.commit()
    logger.info("Bootstrap complete.")


if __name__ == "__main__":
    main()
