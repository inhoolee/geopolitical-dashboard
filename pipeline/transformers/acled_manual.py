"""Transform ACLED manual KPI backfill rows into canonical fact_incident records."""

import logging

import pandas as pd

from pipeline.config import ACLED_MANUAL_KPI_BACKFILL_CSV
from pipeline.utils.id_gen import make_uuid

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = {
    "country_iso3",
    "week_start",
    "event_type",
    "event_count",
    "fatalities_best",
}

OPTIONAL_COLUMNS = {
    "sub_event_type",
    "region_code",
    "source_url",
    "notes",
}

BACKFILL_START = pd.Timestamp("2026-01-01")
BACKFILL_END = pd.Timestamp("2026-02-28")


def transform() -> pd.DataFrame:
    """Read the hand-maintained ACLED KPI backfill CSV."""
    raw = pd.read_csv(ACLED_MANUAL_KPI_BACKFILL_CSV)
    raw.columns = [str(c).strip() for c in raw.columns]

    missing = sorted(REQUIRED_COLUMNS - set(raw.columns))
    if missing:
        raise ValueError(f"{ACLED_MANUAL_KPI_BACKFILL_CSV.name} is missing required columns: {missing}")

    week_start = pd.to_datetime(raw["week_start"], format="%Y-%m-%d", errors="coerce")
    if week_start.isna().any():
        raise ValueError("ACLED manual KPI backfill contains invalid week_start values")
    if ((week_start < BACKFILL_START) | (week_start > BACKFILL_END)).any():
        raise ValueError("ACLED manual KPI backfill week_start must stay within 2026-01-01..2026-02-28")

    country_iso3 = raw["country_iso3"].fillna("").astype(str).str.strip().str.upper()
    event_type = raw["event_type"].fillna("").astype(str).str.strip()
    if (country_iso3 == "").any() or (event_type == "").any():
        raise ValueError("ACLED manual KPI backfill requires non-empty country_iso3 and event_type")

    event_count = pd.to_numeric(raw["event_count"], errors="coerce")
    fatalities_best = pd.to_numeric(raw["fatalities_best"], errors="coerce")
    if event_count.isna().any() or fatalities_best.isna().any():
        raise ValueError("ACLED manual KPI backfill event_count and fatalities_best must be numeric")
    if (event_count < 0).any() or (fatalities_best < 0).any():
        raise ValueError("ACLED manual KPI backfill event_count and fatalities_best must be >= 0")

    source_event_id = (
        week_start.dt.strftime("%Y-%m-%d")
        + "|"
        + country_iso3
        + "|"
        + event_type
    )
    if source_event_id.duplicated().any():
        dupes = sorted(source_event_id[source_event_id.duplicated()].unique())
        raise ValueError(f"Duplicate ACLED manual KPI backfill keys: {dupes}")

    df = pd.DataFrame(index=raw.index)
    df["source_system"] = "ACLED_MANUAL"
    df["source_event_id"] = source_event_id
    df["incident_id"] = df["source_event_id"].apply(lambda x: make_uuid("ACLED_MANUAL", x))
    df["event_date"] = week_start.dt.date
    df["event_date_end"] = None
    df["country_iso3"] = country_iso3
    df["region_code"] = (
        raw["region_code"].fillna("").astype(str).str.strip().replace({"": None})
        if "region_code" in raw.columns
        else None
    )
    df["admin1"] = None
    df["admin2"] = None
    df["location_name"] = None
    df["latitude"] = None
    df["longitude"] = None
    df["geo_precision"] = None
    df["event_type"] = event_type
    df["sub_event_type"] = (
        raw["sub_event_type"].fillna("").astype(str).str.strip().replace({"": None})
        if "sub_event_type" in raw.columns
        else None
    )
    df["disorder_type"] = None
    df["actor1_name"] = None
    df["actor2_name"] = None
    df["interaction_code"] = None
    df["civilian_targeting"] = None
    df["event_count"] = event_count.round().astype(int)
    df["fatalities_best"] = fatalities_best.round().astype(int)
    df["fatalities_low"] = df["fatalities_best"]
    df["fatalities_high"] = df["fatalities_best"]
    df["notes"] = (
        raw["notes"].fillna("").astype(str).str.strip().replace({"": None})
        if "notes" in raw.columns
        else None
    )
    df["source_urls"] = (
        raw["source_url"].fillna("").astype(str).str.strip().replace({"": None})
        if "source_url" in raw.columns
        else None
    )

    logger.info("ACLED manual KPI backfill transformed: %d rows", len(df))
    return df
