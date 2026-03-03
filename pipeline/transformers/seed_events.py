"""Transform the hand-curated diplomatic events seed CSV into fact_diplomatic_action rows."""

import logging

import pandas as pd

from pipeline.config import DIPLOMATIC_SEED_CSV
from pipeline.utils.id_gen import make_uuid

logger = logging.getLogger(__name__)


def transform() -> pd.DataFrame:
    """Read seed CSV and return a DataFrame matching fact_diplomatic_action schema."""
    if not DIPLOMATIC_SEED_CSV.exists():
        logger.warning("Seed CSV not found: %s", DIPLOMATIC_SEED_CSV)
        return pd.DataFrame()

    raw = pd.read_csv(DIPLOMATIC_SEED_CSV, dtype=str, parse_dates=["action_date"])
    logger.info("Seed events raw rows: %d", len(raw))

    df = raw.copy()

    # Re-derive stable IDs regardless of the CSV's action_id column
    df["action_id"] = df.apply(
        lambda r: make_uuid(
            str(r.get("actor_iso3", "")),
            str(r.get("target_iso3", "")),
            str(r.get("action_date", "")),
            str(r.get("action_type", "")),
            str(r.get("instrument_name", "")),
        ),
        axis=1,
    )

    df["action_date"] = pd.to_datetime(raw["action_date"], errors="coerce").dt.date
    df["confidence_flag"] = "HIGH"

    # Ensure all required columns are present
    for col in ["actor_iso3", "target_iso3", "action_type", "action_subtype",
                "instrument_name", "legal_basis", "status", "source_url", "region", "notes"]:
        if col not in df.columns:
            df[col] = None

    result = df[[
        "action_id", "action_date", "actor_iso3", "target_iso3",
        "action_type", "action_subtype", "instrument_name", "legal_basis",
        "status", "confidence_flag", "source_url", "region", "notes",
    ]]

    logger.info("Seed events transformed: %d rows", len(result))
    return result
