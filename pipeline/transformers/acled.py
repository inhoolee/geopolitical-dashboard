"""Transform raw ACLED JSON pages into canonical fact_incident rows."""

import json
import logging

import pandas as pd

from pipeline.config import ACLED_RAW_DIR
from pipeline.utils.id_gen import make_uuid

logger = logging.getLogger(__name__)


def transform() -> pd.DataFrame:
    """Read all ACLED JSON pages and return a DataFrame matching fact_incident schema."""
    json_files = sorted(ACLED_RAW_DIR.glob("*.json"))
    if not json_files:
        logger.warning("No ACLED JSON files found in %s", ACLED_RAW_DIR)
        return pd.DataFrame()

    records = []
    for jf in json_files:
        with open(jf) as fh:
            records.extend(json.load(fh))

    if not records:
        return pd.DataFrame()

    raw = pd.DataFrame(records)
    logger.info("ACLED raw records: %d", len(raw))

    df = pd.DataFrame(index=raw.index)
    df["source_system"] = "ACLED"
    df["source_event_id"] = raw["event_id_cnty"].astype(str)
    df["incident_id"] = raw["event_id_cnty"].apply(lambda x: make_uuid("ACLED", str(x)))

    df["event_date"] = pd.to_datetime(raw["event_date"], errors="coerce").dt.date
    df["event_date_end"] = None

    df["country_iso3"] = raw.get("iso3", raw.get("iso", pd.Series(dtype=str)))
    df["admin1"] = raw.get("admin1", pd.Series(dtype=str))
    df["admin2"] = raw.get("admin2", pd.Series(dtype=str))
    df["location_name"] = raw.get("location", pd.Series(dtype=str))

    df["latitude"] = pd.to_numeric(raw.get("latitude"), errors="coerce")
    df["longitude"] = pd.to_numeric(raw.get("longitude"), errors="coerce")
    df["geo_precision"] = pd.to_numeric(raw.get("geo_precision"), errors="coerce")

    df["event_type"] = raw.get("event_type", pd.Series(dtype=str))
    df["sub_event_type"] = raw.get("sub_event_type", pd.Series(dtype=str))
    df["disorder_type"] = raw.get("disorder_type", pd.Series(dtype=str))

    df["actor1_name"] = raw.get("actor1", pd.Series(dtype=str))
    df["actor2_name"] = raw.get("actor2", pd.Series(dtype=str))
    df["interaction_code"] = raw.get("interaction", pd.Series(dtype=str))

    # ACLED civilian_targeting field: "Civilian targeting" string or empty
    ct = raw.get("civilian_targeting", pd.Series(dtype=str)).fillna("")
    df["civilian_targeting"] = ct.str.lower().str.contains("civilian")

    df["fatalities_best"] = pd.to_numeric(raw.get("fatalities", 0), errors="coerce").fillna(0).astype(int)
    df["fatalities_low"] = df["fatalities_best"]
    df["fatalities_high"] = df["fatalities_best"]

    df["notes"] = raw.get("notes", pd.Series(dtype=str))
    df["source_urls"] = raw.get("source", pd.Series(dtype=str))
    df["region_code"] = None

    before = len(df)
    df = df.dropna(subset=["event_date"])
    logger.info("ACLED transformed: %d rows (dropped %d with null dates)", len(df), before - len(df))
    return df
