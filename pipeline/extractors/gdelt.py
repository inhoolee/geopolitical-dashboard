"""GDELT DOC 2.0 API extractor – batches by quarter for backfill, daily for incremental."""

import json
import logging
from datetime import date, timedelta
from pathlib import Path

import time

import requests

from pipeline.config import (
    GDELT_BASE_URL, GDELT_MAX_RECORDS, GDELT_THEMES, GDELT_RAW_DIR,
    DASHBOARD_START_DATE,
)
from pipeline.extractors.base import BaseExtractor
from pipeline.utils.retry import retry

logger = logging.getLogger(__name__)

# Seconds to sleep between API calls to avoid rate-limiting
_SLEEP_BETWEEN_CALLS = 2.0
# Simplified single-theme query to reduce API load per call
_SIMPLE_THEME_QUERY = "(theme:MILITARY OR theme:SANCTION OR theme:DIPLOMACY)"


def _quarter_windows(start: date, end: date) -> list[tuple[date, date]]:
    """Split a date range into ~90-day windows (GDELT's practical max lookback)."""
    windows = []
    current = start
    while current < end:
        window_end = min(current + timedelta(days=89), end)
        windows.append((current, window_end))
        current = window_end + timedelta(days=1)
    return windows


class GDELTExtractor(BaseExtractor):
    SOURCE_NAME = "GDELT_DOC"

    def extract(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        **kwargs,
    ) -> None:
        """
        Fetch GDELT articles for the recent window.

        NOTE: The GDELT DOC 2.0 API only reliably serves the last ~90 days.
        For historical backfill (2017+), the GDELT Event Database bulk files on
        Google Cloud Storage (gs://gdelt-open-data/) would be required instead.
        This extractor fetches only the recent 90-day window for the news pulse panel.
        """
        GDELT_RAW_DIR.mkdir(parents=True, exist_ok=True)
        end = end_date or date.today()
        # Cap start to at most 88 days back (GDELT's reliable range)
        max_lookback = end - timedelta(days=88)
        start = max(start_date or max_lookback, max_lookback)

        windows = _quarter_windows(start, end)
        logger.info(
            "GDELT fetch: %d window(s) (%s → %s) [recent 90-day window only]",
            len(windows), start, end,
        )

        for i, (window_start, window_end) in enumerate(windows):
            self._fetch_window(_SIMPLE_THEME_QUERY, window_start, window_end)
            if i < len(windows) - 1:
                time.sleep(_SLEEP_BETWEEN_CALLS)

    def _fetch_window(self, query: str, start: date, end: date) -> None:
        tag = f"{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}"
        out_file = GDELT_RAW_DIR / f"artlist_{tag}.json"

        if out_file.exists():
            logger.debug("GDELT window %s already cached – skipping", tag)
            return

        params = {
            "query": query,
            "mode": "ArtList",
            "maxrecords": GDELT_MAX_RECORDS,
            "startdatetime": start.strftime("%Y%m%d") + "000000",
            "enddatetime": end.strftime("%Y%m%d") + "235959",
            "format": "json",
            "sort": "DateDesc",
        }

        try:
            data = self._get_json(params)
            with open(out_file, "w") as fh:
                json.dump(data, fh)
            article_count = len((data or {}).get("articles", []))
            logger.info("GDELT %s: %d articles saved", tag, article_count)
        except Exception as exc:
            logger.warning("GDELT window %s failed: %s", tag, exc)

    _HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
    }

    @retry(max_attempts=3, backoff_base=5.0, exceptions=(requests.RequestException,))
    def _get_json(self, params: dict) -> dict:
        resp = requests.get(GDELT_BASE_URL, params=params, headers=self._HEADERS, timeout=60)
        resp.raise_for_status()
        text = resp.text.strip()
        if not text:
            return {}
        return resp.json()
