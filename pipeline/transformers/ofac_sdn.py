"""Transform OFAC SDN CSV into canonical fact_diplomatic_action rows."""

import logging
from datetime import date, timezone
from datetime import datetime

import pandas as pd

from pipeline.config import OFAC_RAW_DIR
from pipeline.utils.id_gen import make_uuid
from pipeline.utils.iso3 import name_to_iso3

logger = logging.getLogger(__name__)

SDN_FILENAME = "sdn.csv"

# OFAC SDN CSV column positions (0-indexed, no header row)
# Ref: https://www.treasury.gov/ofac/downloads/sdnlist.txt
SDN_COLUMNS = [
    "ent_num", "sdn_name", "sdn_type", "program",
    "title", "call_sign", "vess_type", "tonnage", "grt",
    "vess_flag", "vess_owner", "remarks",
]

# Map OFAC program codes to rough target country ISO3
_PROGRAM_TO_ISO3: dict[str, str] = {
    "RUSSIA-EO14024": "RUS",
    "UKRAINE-EO13685": "RUS",  # Crimea-related = Russia-origin
    "IRAN": "IRN",
    "IRAN2": "IRN",
    "NPWMD": None,  # Non-proliferation – no single target
    "SDGT": None,   # Terrorism – no single target
    "SYRIA": "SYR",
    "DPRK": "PRK",
    "DPRK2": "PRK",
    "DPRK3": "PRK",
    "DPRK4": "PRK",
    "VENEZUELA": "VEN",
    "VENEZUELA2": "VEN",
    "BURMA": "MMR",
    "BELARUS": "BLR",
    "SUDAN": "SDN",
    "IRAQ2": "IRQ",
    "LIBYA2": "LBY",
    "SOMALIA": "SOM",
    "YEMEN": "YEM",
    "GLOMAG": None,  # Global Magnitsky – various
    "CYBER2": None,
}

TODAY = date.today()


def _infer_target_iso3(program: str) -> str | None:
    if not program:
        return None
    prog_upper = program.strip().upper()
    # Exact lookup first
    if prog_upper in _PROGRAM_TO_ISO3:
        return _PROGRAM_TO_ISO3[prog_upper]
    # Prefix match
    for key, val in _PROGRAM_TO_ISO3.items():
        if prog_upper.startswith(key):
            return val
    return None


def transform() -> pd.DataFrame:
    """Read OFAC SDN CSV and return a DataFrame matching fact_diplomatic_action schema."""
    sdn_path = OFAC_RAW_DIR / SDN_FILENAME
    if not sdn_path.exists():
        logger.warning("OFAC SDN CSV not found: %s", sdn_path)
        return pd.DataFrame()

    # SDN CSV has no header; use first N column names
    try:
        raw = pd.read_csv(
            sdn_path,
            header=None,
            names=SDN_COLUMNS,
            on_bad_lines="skip",
            encoding="latin-1",
            dtype=str,
        )
    except Exception as exc:
        logger.error("Failed to read OFAC SDN CSV: %s", exc)
        return pd.DataFrame()

    # Replace OFAC null placeholder
    raw = raw.replace("-0-", None)
    logger.info("OFAC SDN raw rows: %d", len(raw))

    rows = []
    for _, row in raw.iterrows():
        programs = str(row.get("program") or "").split(";")
        for prog in programs:
            prog = prog.strip()
            target = _infer_target_iso3(prog)
            instrument = f"SDN: {row.get('sdn_name', '')} ({prog})"
            rows.append({
                "action_id": make_uuid("OFAC_SDN", str(row.get("ent_num", "")), prog),
                "action_date": TODAY,          # Best available; SDN CSV has no designation date
                "actor_iso3": "USA",
                "target_iso3": target,
                "action_type": "sanction",
                "action_subtype": "OFAC_SDN",
                "instrument_name": instrument[:255],
                "legal_basis": prog,
                "status": "active",
                "confidence_flag": "LOW",      # Date is ingestion date, not designation date
                "source_url": "https://www.treasury.gov/ofac/downloads/sdn.csv",
                "region": None,
                "notes": row.get("remarks"),
            })

    df = pd.DataFrame(rows) if rows else pd.DataFrame()
    logger.info("OFAC SDN transformed: %d action rows", len(df))
    return df
