"""Transform raw UCDP GED CSV into canonical fact_incident rows."""

import logging
import zipfile
from pathlib import Path

import pandas as pd

from pipeline.config import UCDP_RAW_DIR
from pipeline.utils.id_gen import make_uuid
from pipeline.utils.iso3 import name_to_iso3

logger = logging.getLogger(__name__)

ZIP_NAME = "ged251-csv.zip"

# Map UCDP type_of_violence codes to descriptive labels
VIOLENCE_TYPE_MAP = {
    1: "state-based conflict",
    2: "non-state conflict",
    3: "one-sided violence",
}


def _extract_csv(zip_path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(zip_path) as zf:
        csv_names = [n for n in zf.namelist() if n.endswith(".csv")]
        if not csv_names:
            raise ValueError(f"No CSV found inside {zip_path}")
        logger.info("Reading UCDP GED CSV: %s", csv_names[0])
        with zf.open(csv_names[0]) as fh:
            return pd.read_csv(fh, dtype=str, low_memory=False)


def transform() -> pd.DataFrame:
    """Return a DataFrame matching the fact_incident schema."""
    zip_path = UCDP_RAW_DIR / ZIP_NAME
    if not zip_path.exists():
        raise FileNotFoundError(f"UCDP GED zip not found: {zip_path}. Run the extractor first.")

    raw = _extract_csv(zip_path)
    logger.info("UCDP GED raw rows: %d", len(raw))

    df = pd.DataFrame(index=raw.index)
    df["source_system"] = "UCDP_GED"
    df["source_event_id"] = raw["id"].astype(str)
    df["incident_id"] = raw["id"].apply(lambda x: make_uuid("UCDP_GED", str(x)))

    df["event_date"] = pd.to_datetime(raw["date_start"], errors="coerce").dt.date
    df["event_date_end"] = pd.to_datetime(raw["date_end"], errors="coerce").dt.date

    # ISO3 from country name
    df["country_iso3"] = raw["country"].apply(name_to_iso3)

    df["admin1"] = raw.get("adm_1", pd.Series(dtype=str))
    df["admin2"] = raw.get("adm_2", pd.Series(dtype=str))
    df["location_name"] = raw.get("where_description", pd.Series(dtype=str))

    df["latitude"] = pd.to_numeric(raw["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(raw["longitude"], errors="coerce")
    df["geo_precision"] = pd.to_numeric(raw["where_prec"], errors="coerce")

    violence_type_num = pd.to_numeric(raw["type_of_violence"], errors="coerce")
    df["event_type"] = violence_type_num.map(VIOLENCE_TYPE_MAP)
    df["sub_event_type"] = None
    df["disorder_type"] = None

    # UCDP stores dyad_name for the conflict pair; split into actor1/actor2
    dyad = raw.get("dyad_name", pd.Series(dtype=str)).fillna("")
    df["actor1_name"] = dyad.str.split(" - ").str[0].str.strip().replace("", None)
    df["actor2_name"] = dyad.str.split(" - ").str[1].str.strip().replace("", None)
    df["interaction_code"] = None

    # Civilian targeting: UCDP one-sided violence (type 3) always has civilians as target
    df["civilian_targeting"] = violence_type_num == 3

    deaths_best = pd.to_numeric(raw.get("best", raw.get("deaths_best", "0")), errors="coerce").fillna(0)
    deaths_low = pd.to_numeric(raw.get("low", "0"), errors="coerce").fillna(0)
    deaths_high = pd.to_numeric(raw.get("high", "0"), errors="coerce").fillna(0)
    df["fatalities_best"] = deaths_best.astype(int)
    df["fatalities_low"] = deaths_low.astype(int)
    df["fatalities_high"] = deaths_high.astype(int)

    df["notes"] = None
    df["source_urls"] = raw.get("source_article", pd.Series(dtype=str))
    df["region_code"] = None  # populated later by dim_country join

    # Drop rows with no valid date
    before = len(df)
    df = df.dropna(subset=["event_date"])
    logger.info("UCDP GED transformed: %d rows (dropped %d with null dates)", len(df), before - len(df))
    return df
