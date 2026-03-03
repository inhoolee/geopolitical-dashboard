"""ACLED API extractor – requires ACLED_API_KEY and ACLED_EMAIL env vars."""

import json
import logging
from datetime import date
from pathlib import Path

import requests

from pipeline.config import (
    ACLED_API_KEY, ACLED_EMAIL, ACLED_BASE_URL, ACLED_PAGE_SIZE,
    ACLED_RAW_DIR, DASHBOARD_START_DATE,
)
from pipeline.extractors.base import BaseExtractor
from pipeline.utils.retry import retry

logger = logging.getLogger(__name__)

ACLED_FIELDS = "|".join([
    "event_id_cnty", "event_date", "event_type", "sub_event_type",
    "disorder_type", "actor1", "actor2", "interaction", "country",
    "iso3", "admin1", "admin2", "location", "latitude", "longitude",
    "geo_precision", "civilian_targeting", "fatalities", "notes",
    "source", "source_scale",
])


class ACLEDExtractor(BaseExtractor):
    SOURCE_NAME = "ACLED"

    def is_available(self) -> bool:
        if not (ACLED_API_KEY and ACLED_EMAIL):
            logger.warning(
                "ACLED credentials not set. Set ACLED_API_KEY and ACLED_EMAIL "
                "environment variables (register at https://acleddata.com/register/)"
            )
            return False
        return True

    def extract(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        **kwargs,
    ) -> None:
        ACLED_RAW_DIR.mkdir(parents=True, exist_ok=True)
        start = start_date or DASHBOARD_START_DATE
        end = end_date or date.today()
        start_str = start.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")

        logger.info("ACLED extraction: %s → %s", start_str, end_str)
        page = 1
        total_saved = 0

        while True:
            params = {
                "key": ACLED_API_KEY,
                "email": ACLED_EMAIL,
                "event_date": f"{start_str}|{end_str}",
                "event_date_where": "BETWEEN",
                "limit": ACLED_PAGE_SIZE,
                "page": page,
                "format": "json",
                "fields": ACLED_FIELDS,
            }
            data = self._get_json(params)
            records = data.get("data", [])
            if not records:
                break

            out_file = ACLED_RAW_DIR / f"{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}_page{page:04d}.json"
            with open(out_file, "w") as fh:
                json.dump(records, fh)

            total_saved += len(records)
            logger.info("ACLED page %d: %d records (total %d)", page, len(records), total_saved)

            if len(records) < ACLED_PAGE_SIZE:
                break
            page += 1

        logger.info("ACLED extraction complete: %d records", total_saved)

    @retry(max_attempts=4, backoff_base=3.0, exceptions=(requests.RequestException,))
    def _get_json(self, params: dict) -> dict:
        resp = requests.get(ACLED_BASE_URL, params=params, timeout=60)
        resp.raise_for_status()
        return resp.json()
