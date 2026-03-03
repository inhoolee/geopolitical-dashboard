"""Transform World Bank API JSON pages into canonical fact_risk_indicator rows."""

import json
import logging
from datetime import date

import pandas as pd

from pipeline.config import WB_RAW_DIR, WB_INDICATORS
from pipeline.utils.iso3 import wb_code_to_iso3

logger = logging.getLogger(__name__)


def transform() -> pd.DataFrame:
    """Read all WB JSON pages and return a DataFrame matching fact_risk_indicator schema."""
    all_rows = []

    for indicator_code, indicator_name in WB_INDICATORS.items():
        ind_dir = WB_RAW_DIR / indicator_code
        if not ind_dir.exists():
            logger.warning("WB indicator directory not found: %s", ind_dir)
            continue

        pages = sorted(ind_dir.glob("page_*.json"))
        for page_file in pages:
            with open(page_file) as fh:
                data = json.load(fh)
            for item in data:
                if item is None or item.get("value") is None:
                    continue
                country_code = (item.get("countryiso3code") or "").upper()
                if not country_code:
                    # Fall back to 2-letter code
                    alpha2 = (item.get("country", {}) or {}).get("id", "")
                    country_code = wb_code_to_iso3(alpha2) or ""

                year_str = item.get("date", "")
                if not year_str or not year_str.isdigit():
                    continue

                all_rows.append({
                    "country_iso3": country_code,
                    "period_start": date(int(year_str), 1, 1),
                    "indicator_code": indicator_code,
                    "indicator_name": indicator_name,
                    "value": float(item["value"]),
                    "unit": item.get("unit", ""),
                    "source_system": "WORLD_BANK",
                    "source_url": f"https://data.worldbank.org/indicator/{indicator_code}",
                })

    if not all_rows:
        logger.warning("No World Bank data rows found")
        return pd.DataFrame()

    df = pd.DataFrame(all_rows)
    logger.info("World Bank transformed: %d rows across %d indicators", len(df), df["indicator_code"].nunique())
    return df
