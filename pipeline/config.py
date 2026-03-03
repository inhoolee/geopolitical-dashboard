"""Central configuration: env vars, paths, URLs, indicator codes, date constants."""

import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent
DATA_ROOT = PROJECT_ROOT / "data"
RAW_ROOT = DATA_ROOT / "raw"
SEEDS_PATH = DATA_ROOT / "seeds"
WAREHOUSE_PATH = Path(os.getenv("WAREHOUSE_PATH", str(DATA_ROOT / "warehouse" / "geopolitical.duckdb")))
SQL_SCHEMA_DIR = PROJECT_ROOT / "sql" / "schema"
SQL_QUERIES_DIR = PROJECT_ROOT / "sql" / "queries"

# ---------------------------------------------------------------------------
# Date boundary
# ---------------------------------------------------------------------------
DASHBOARD_START_DATE = date(2017, 1, 20)  # Trump's first inauguration

# ---------------------------------------------------------------------------
# ACLED (local CSV snapshots)
# ---------------------------------------------------------------------------
ACLED_RAW_DIR = RAW_ROOT / "acled"
ACLED_REGIONAL_CSV_GLOB = "*_aggregated_data_up_to-*.csv"
ACLED_SUMMARY_CSV_PREFIX = "number_of_"

# ---------------------------------------------------------------------------
# UCDP GED
# ---------------------------------------------------------------------------
UCDP_GED_URL = "https://ucdp.uu.se/downloads/ged/ged251-csv.zip"
UCDP_RAW_DIR = RAW_ROOT / "ucdp_ged"
UCDP_COVERAGE_END = date(2024, 12, 31)

# ---------------------------------------------------------------------------
# World Bank
# ---------------------------------------------------------------------------
WB_BASE_URL = "https://api.worldbank.org/v2"
WB_PER_PAGE = 1000
WB_DATE_RANGE = "2010:2025"
WB_RAW_DIR = RAW_ROOT / "world_bank"
WB_INDICATORS: dict[str, str] = {
    "SP.POP.TOTL": "population_total",
    "NY.GDP.PCAP.CD": "gdp_per_capita_usd",
    "MS.MIL.XPND.GD.ZS": "military_exp_pct_gdp",
}

# ---------------------------------------------------------------------------
# GDELT DOC 2.0
# ---------------------------------------------------------------------------
GDELT_BASE_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
GDELT_MAX_RECORDS = 250
GDELT_RAW_DIR = RAW_ROOT / "gdelt"
# Themes for geopolitical topic filtering
GDELT_THEMES = [
    "MILITARY",
    "SANCTIONS",
    "DIPLOMACY",
    "TERROR",
    "POLITICAL_TURMOIL",
    "UNGOV",
]

# ---------------------------------------------------------------------------
# OFAC SDN
# ---------------------------------------------------------------------------
OFAC_SDN_URL = "https://www.treasury.gov/ofac/downloads/sdn.csv"
OFAC_RAW_DIR = RAW_ROOT / "ofac"

# ---------------------------------------------------------------------------
# Seed events
# ---------------------------------------------------------------------------
DIPLOMATIC_SEED_CSV = SEEDS_PATH / "diplomatic_events_seed.csv"
