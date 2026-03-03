"""Populate dim_country and dim_date from pycountry and a date spine."""

import logging
import sys
from datetime import date, timedelta
from pathlib import Path

import pycountry

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.db import get_connection
from pipeline.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)

# ISO3 → region_code mapping for high-priority countries
# Remaining countries default to the region detected from UN M49 groupings (approximated)
_ISO3_TO_REGION: dict[str, str] = {
    # Europe and Eurasia
    "RUS": "EU_EUR", "UKR": "EU_EUR", "GBR": "EU_EUR", "DEU": "EU_EUR",
    "FRA": "EU_EUR", "POL": "EU_EUR", "FIN": "EU_EUR", "SWE": "EU_EUR",
    "NOR": "EU_EUR", "TUR": "EU_EUR", "AZE": "EU_EUR", "ARM": "EU_EUR",
    "GEO": "EU_EUR", "BLR": "EU_EUR", "MDA": "EU_EUR", "SRB": "EU_EUR",
    "KAZ": "EU_EUR", "UZB": "EU_EUR",
    # Middle East and North Africa
    "ISR": "MENA", "PSE": "MENA", "IRN": "MENA", "IRQ": "MENA",
    "SYR": "MENA", "SAU": "MENA", "YEM": "MENA", "LBN": "MENA",
    "JOR": "MENA", "EGY": "MENA", "LBY": "MENA", "TUN": "MENA",
    "DZA": "MENA", "MAR": "MENA", "ARE": "MENA", "OMN": "MENA",
    "QAT": "MENA", "KWT": "MENA", "BHR": "MENA",
    # Sub-Saharan Africa
    "ETH": "SSA", "SDN": "SSA", "SSD": "SSA", "SOM": "SSA",
    "NGA": "SSA", "MLI": "SSA", "BFA": "SSA", "NER": "SSA",
    "TCD": "SSA", "CAF": "SSA", "COD": "SSA", "MOZ": "SSA",
    "ZAF": "SSA", "KEN": "SSA", "TZA": "SSA", "UGA": "SSA",
    "RWA": "SSA", "ZWE": "SSA", "COG": "SSA", "CMR": "SSA",
    "GNB": "SSA", "GIN": "SSA", "HTI": "AME",
    # South and Central Asia
    "AFG": "SCA", "PAK": "SCA", "IND": "SCA", "BGD": "SCA",
    "NPL": "SCA", "LKA": "SCA", "MMR": "SCA",
    # East Asia and Pacific
    "CHN": "EAP", "TWN": "EAP", "PRK": "EAP", "KOR": "EAP",
    "JPN": "EAP", "PHL": "EAP", "VNM": "EAP", "MYS": "EAP",
    "IDN": "EAP", "THA": "EAP", "AUS": "EAP", "NZL": "EAP",
    "SGP": "EAP", "PNG": "EAP",
    # Americas
    "USA": "AME", "MEX": "AME", "CAN": "AME", "VEN": "AME",
    "COL": "AME", "BRA": "AME", "ARG": "AME", "CHL": "AME",
    "PER": "AME", "BOL": "AME", "ECU": "AME", "CUB": "AME",
    "NIC": "AME", "HND": "AME", "GTM": "AME", "SLV": "AME",
}


def _region_for_iso3(iso3: str) -> str | None:
    return _ISO3_TO_REGION.get(iso3)


def populate_countries(conn) -> None:
    logger.info("Seeding dim_country…")
    rows = []
    for country in pycountry.countries:
        iso3 = country.alpha_3
        iso2 = country.alpha_2
        name = country.name
        region = _region_for_iso3(iso3)
        rows.append((iso3, iso2, name, region))

    # Add special/quasi-country codes used in the pipeline
    extras = [
        ("EUU", "EU", "European Union", "EU_EUR"),
        ("NAT", None, "NATO", "EU_EUR"),
        ("UNO", None, "United Nations", "GLO"),
        ("XKX", "XK", "Kosovo", "EU_EUR"),
        ("TWN", "TW", "Taiwan", "EAP"),
        ("PSE", "PS", "Palestinian Territories", "MENA"),
    ]
    for row in extras:
        rows.append(row)

    for row in rows:
        conn.execute(
            "INSERT OR IGNORE INTO dim_country (iso3, iso2, name, region_code) VALUES (?, ?, ?, ?)",
            row,
        )

    conn.commit()
    logger.info("dim_country: %d rows", conn.execute("SELECT COUNT(*) FROM dim_country").fetchone()[0])


def populate_date_spine(conn, start: date = date(2010, 1, 1), end: date = date(2030, 12, 31)) -> None:
    logger.info("Seeding dim_date (%s → %s)…", start, end)
    current = start
    batch = []
    while current <= end:
        iso_cal = current.isocalendar()
        batch.append((
            current,
            current.year,
            current.month,
            (current.month - 1) // 3 + 1,
            iso_cal.week,
            current.weekday(),     # 0 = Monday
            current.weekday() >= 5,
        ))
        current += timedelta(days=1)

        if len(batch) >= 5000:
            conn.executemany(
                "INSERT OR IGNORE INTO dim_date VALUES (?, ?, ?, ?, ?, ?, ?)", batch
            )
            batch.clear()

    if batch:
        conn.executemany(
            "INSERT OR IGNORE INTO dim_date VALUES (?, ?, ?, ?, ?, ?, ?)", batch
        )

    conn.commit()
    logger.info("dim_date: %d rows", conn.execute("SELECT COUNT(*) FROM dim_date").fetchone()[0])


def populate_event_types(conn) -> None:
    """Seed known event type codes for ACLED and UCDP."""
    event_types = [
        # ACLED
        ("ACLED_BATTLES", "Battles", "ACLED", "Violent Events"),
        ("ACLED_EXPLOSIONS", "Explosions/Remote violence", "ACLED", "Violent Events"),
        ("ACLED_VIOLENCE_CIVILIANS", "Violence against civilians", "ACLED", "Violent Events"),
        ("ACLED_PROTESTS", "Protests", "ACLED", "Demonstrations"),
        ("ACLED_RIOTS", "Riots", "ACLED", "Demonstrations"),
        ("ACLED_STRATEGIC_DEV", "Strategic developments", "ACLED", "Non-violent"),
        # UCDP
        ("UCDP_STATE_BASED", "State-based conflict", "UCDP_GED", None),
        ("UCDP_NON_STATE", "Non-state conflict", "UCDP_GED", None),
        ("UCDP_ONE_SIDED", "One-sided violence", "UCDP_GED", None),
    ]
    for row in event_types:
        conn.execute(
            "INSERT OR IGNORE INTO dim_event_type (event_type_code, label, source_system, parent_type) VALUES (?, ?, ?, ?)",
            row,
        )
    conn.commit()


def main() -> None:
    setup_logging()
    conn = get_connection()
    populate_countries(conn)
    populate_date_spine(conn)
    populate_event_types(conn)
    logger.info("Dimension seeding complete.")


if __name__ == "__main__":
    main()
