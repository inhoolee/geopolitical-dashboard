"""World Bank API extractor – fetches WDI indicator series for all countries."""

import json
import logging
from pathlib import Path

import requests

from pipeline.config import WB_BASE_URL, WB_PER_PAGE, WB_DATE_RANGE, WB_INDICATORS, WB_RAW_DIR
from pipeline.extractors.base import BaseExtractor
from pipeline.utils.retry import retry

logger = logging.getLogger(__name__)


class WorldBankExtractor(BaseExtractor):
    SOURCE_NAME = "WORLD_BANK"

    def extract(self, force: bool = False, **kwargs) -> None:
        WB_RAW_DIR.mkdir(parents=True, exist_ok=True)
        for indicator_code in WB_INDICATORS:
            self._fetch_indicator(indicator_code, force=force)

    def _fetch_indicator(self, indicator_code: str, force: bool = False) -> None:
        out_dir = WB_RAW_DIR / indicator_code
        out_dir.mkdir(parents=True, exist_ok=True)
        page1_file = out_dir / "page_001.json"

        if page1_file.exists() and not force:
            logger.info("WB %s already downloaded – skipping", indicator_code)
            return

        logger.info("Fetching World Bank indicator: %s", indicator_code)
        url = f"{WB_BASE_URL}/country/all/indicator/{indicator_code}"
        params: dict = {
            "format": "json",
            "per_page": WB_PER_PAGE,
            "date": WB_DATE_RANGE,
            "page": 1,
        }

        # First page to get total pages
        first_response = self._get_json(url, params)
        if not isinstance(first_response, list) or len(first_response) < 2:
            logger.error("Unexpected WB response structure for %s", indicator_code)
            return

        meta, data = first_response
        total_pages = meta.get("pages", 1)
        self._save_page(out_dir, 1, data)
        logger.debug("WB %s: page 1/%d saved (%d records)", indicator_code, total_pages, len(data or []))

        for page in range(2, total_pages + 1):
            params["page"] = page
            response = self._get_json(url, params)
            if isinstance(response, list) and len(response) == 2:
                self._save_page(out_dir, page, response[1])
                logger.debug("WB %s: page %d/%d saved", indicator_code, page, total_pages)

        logger.info("WB %s: complete (%d pages)", indicator_code, total_pages)

    @retry(max_attempts=4, backoff_base=2.0, exceptions=(requests.RequestException,))
    def _get_json(self, url: str, params: dict) -> list:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _save_page(out_dir: Path, page: int, data: list | None) -> None:
        path = out_dir / f"page_{page:03d}.json"
        with open(path, "w") as fh:
            json.dump(data or [], fh)
