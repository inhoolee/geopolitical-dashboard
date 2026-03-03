"""Transform ACLED local regional aggregate CSVs into canonical fact_incident rows."""

import logging

import pandas as pd

from pipeline.config import ACLED_RAW_DIR, ACLED_REGIONAL_CSV_GLOB, ACLED_SUMMARY_CSV_PREFIX
from pipeline.utils.id_gen import make_uuid
from pipeline.utils.iso3 import name_to_iso3

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = {
    "WEEK",
    "REGION",
    "COUNTRY",
    "ADMIN1",
    "EVENT_TYPE",
    "SUB_EVENT_TYPE",
    "EVENTS",
    "FATALITIES",
    "DISORDER_TYPE",
    "ID",
    "CENTROID_LATITUDE",
    "CENTROID_LONGITUDE",
}


def _normalized_id(series: pd.Series) -> pd.Series:
    text = series.fillna("").astype(str).str.strip()
    numeric = pd.to_numeric(text, errors="coerce")
    int_mask = numeric.notna() & (numeric % 1 == 0)
    if int_mask.any():
        text.loc[int_mask] = numeric.loc[int_mask].astype("Int64").astype(str)
    return text


def transform() -> pd.DataFrame:
    """Read ACLED regional aggregate CSVs and return fact_incident rows."""
    csv_files = [
        p
        for p in sorted(ACLED_RAW_DIR.glob(ACLED_REGIONAL_CSV_GLOB))
        if not p.name.startswith(ACLED_SUMMARY_CSV_PREFIX)
    ]
    if not csv_files:
        logger.warning("No ACLED regional CSV files found in %s", ACLED_RAW_DIR)
        return pd.DataFrame()

    frames: list[pd.DataFrame] = []
    for csv_path in csv_files:
        raw = pd.read_csv(csv_path)
        raw.columns = [str(c).strip().upper() for c in raw.columns]
        missing = sorted(REQUIRED_COLUMNS - set(raw.columns))
        if missing:
            raise ValueError(f"{csv_path.name} is missing required columns: {missing}")
        raw["__source_file"] = csv_path.name
        frames.append(raw)
        logger.info("ACLED regional CSV %s: %d rows", csv_path.name, len(raw))

    raw = pd.concat(frames, ignore_index=True)
    logger.info("ACLED raw aggregate rows: %d", len(raw))

    week = pd.to_datetime(raw["WEEK"], format="%Y-%m-%d", errors="coerce")
    week_key = week.dt.strftime("%Y-%m-%d").fillna("")
    country = raw["COUNTRY"].fillna("").astype(str).str.strip()
    admin1 = raw["ADMIN1"].fillna("").astype(str).str.strip()
    event_type = raw["EVENT_TYPE"].fillna("").astype(str).str.strip()
    sub_event_type = raw["SUB_EVENT_TYPE"].fillna("").astype(str).str.strip()
    source_id = _normalized_id(raw["ID"])

    event_count = pd.to_numeric(raw["EVENTS"], errors="coerce")
    fatalities = pd.to_numeric(raw["FATALITIES"], errors="coerce").fillna(0)

    df = pd.DataFrame(index=raw.index)
    df["source_system"] = "ACLED"
    df["source_event_id"] = (
        week_key + "|" + country + "|" + admin1 + "|" + event_type + "|" + sub_event_type + "|" + source_id
    )
    df["incident_id"] = df["source_event_id"].apply(lambda x: make_uuid("ACLED", x))

    df["event_date"] = week.dt.date
    df["event_date_end"] = None

    df["country_iso3"] = country.apply(name_to_iso3)
    df["admin1"] = admin1.replace("", None)
    df["admin2"] = None
    df["location_name"] = df["admin1"]

    df["latitude"] = pd.to_numeric(raw["CENTROID_LATITUDE"], errors="coerce")
    df["longitude"] = pd.to_numeric(raw["CENTROID_LONGITUDE"], errors="coerce")
    df["geo_precision"] = None

    df["event_type"] = event_type.replace("", None)
    df["sub_event_type"] = sub_event_type.replace("", None)
    df["disorder_type"] = raw["DISORDER_TYPE"].fillna("").astype(str).str.strip().replace("", None)

    df["actor1_name"] = None
    df["actor2_name"] = None
    df["interaction_code"] = None
    df["civilian_targeting"] = event_type.str.lower().eq("violence against civilians")

    df["event_count"] = event_count.round().astype("Int64")
    df["fatalities_best"] = fatalities.round().astype("Int64")
    df["fatalities_low"] = df["fatalities_best"]
    df["fatalities_high"] = df["fatalities_best"]

    df["notes"] = "ACLED weekly aggregate (local CSV snapshot)"
    df["source_urls"] = None
    df["region_code"] = None

    before = len(df)
    valid = df["event_date"].notna() & df["event_count"].notna() & (df["event_count"] >= 0)
    df = df.loc[valid].copy()

    for col in ["event_count", "fatalities_best", "fatalities_low", "fatalities_high"]:
        df[col] = df[col].fillna(0).astype(int)

    logger.info(
        "ACLED transformed: %d rows (dropped %d invalid rows)",
        len(df),
        before - len(df),
    )
    return df
