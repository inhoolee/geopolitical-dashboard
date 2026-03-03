"""Transform GDELT DOC 2.0 ArtList JSON files into canonical fact_news_pulse rows."""

import json
import logging
from datetime import timezone

import pandas as pd

from pipeline.config import GDELT_RAW_DIR
from pipeline.utils.id_gen import make_uuid
from pipeline.utils.iso3 import iso2_to_iso3

logger = logging.getLogger(__name__)

# GDELT uses FIPS 2-char country codes; map a few common ones
_FIPS_EXTRA: dict[str, str] = {
    "IZ": "IRQ", "IR": "IRN", "SY": "SYR", "RS": "RUS",
    "CH": "CHN", "KN": "PRK", "KS": "KOR", "UP": "UKR",
    "UK": "GBR", "FR": "FRA", "GM": "DEU", "IS": "ISR",
    "JA": "JPN", "PK": "PAK", "AF": "AFG", "IN": "IND",
    "LE": "LBN", "EG": "EGY", "SA": "SAU", "YM": "YEM",
    "SO": "SOM", "SU": "SDN", "LY": "LBY", "ET": "ETH",
    "ML": "MLI", "NI": "NER", "BK": "BFA",
}


def _fips_to_iso3(fips: str) -> str | None:
    if not fips:
        return None
    fips = fips.upper().strip()
    if fips in _FIPS_EXTRA:
        return _FIPS_EXTRA[fips]
    return iso2_to_iso3(fips)


def transform() -> pd.DataFrame:
    """Read all GDELT ArtList JSON files and return a DataFrame matching fact_news_pulse schema."""
    json_files = sorted(GDELT_RAW_DIR.glob("artlist_*.json"))
    if not json_files:
        logger.warning("No GDELT artlist JSON files found in %s", GDELT_RAW_DIR)
        return pd.DataFrame()

    all_articles = []
    for jf in json_files:
        with open(jf) as fh:
            data = json.load(fh)
        articles = data.get("articles", []) if isinstance(data, dict) else []
        all_articles.extend(articles)

    if not all_articles:
        return pd.DataFrame()

    raw = pd.DataFrame(all_articles)
    logger.info("GDELT raw articles: %d", len(raw))

    df = pd.DataFrame(index=raw.index)
    df["item_id"] = raw.apply(
        lambda r: make_uuid(str(r.get("url", "")), str(r.get("seendate", ""))), axis=1
    )

    # Parse GDELT date format: YYYYMMDDTHHMMSSZ
    df["published_at_utc"] = pd.to_datetime(
        raw.get("seendate", pd.Series(dtype=str)), format="%Y%m%dT%H%M%SZ", errors="coerce", utc=True
    )

    df["country_focus_iso3"] = raw.get("sourcecountry", pd.Series(dtype=str)).apply(_fips_to_iso3)
    df["region_code"] = None

    df["title"] = raw.get("title", pd.Series(dtype=str))
    df["source_domain"] = raw.get("domain", pd.Series(dtype=str))
    df["url"] = raw.get("url", pd.Series(dtype=str))

    # Build topic tags from GDELT themes if present
    df["topic_tags"] = raw.get("themes", raw.get("tone", pd.Series(dtype=str))).apply(
        lambda x: str(x)[:500] if pd.notna(x) else None
    )

    df["attention_count"] = 1  # per-article; aggregate in DuckDB views
    df["tone"] = pd.to_numeric(raw.get("tone", None), errors="coerce")

    before = len(df)
    df = df.drop_duplicates(subset=["item_id"])
    logger.info("GDELT transformed: %d articles (dropped %d duplicates)", len(df), before - len(df))
    return df
