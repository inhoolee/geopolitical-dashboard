"""UCDP GED v25.1 extractor – downloads the zip if not already present."""

import logging
from pathlib import Path

import requests

from pipeline.config import UCDP_GED_URL, UCDP_RAW_DIR
from pipeline.extractors.base import BaseExtractor
from pipeline.utils.retry import retry

logger = logging.getLogger(__name__)

ZIP_NAME = "ged251-csv.zip"


class UCDPGEDExtractor(BaseExtractor):
    SOURCE_NAME = "UCDP_GED"

    def extract(self, force: bool = False, **kwargs) -> None:
        UCDP_RAW_DIR.mkdir(parents=True, exist_ok=True)
        dest = UCDP_RAW_DIR / ZIP_NAME

        if dest.exists() and not force:
            logger.info("UCDP GED zip already present at %s – skipping download", dest)
            return

        logger.info("Downloading UCDP GED v25.1 from %s", UCDP_GED_URL)
        self._download(dest)
        logger.info("UCDP GED download complete: %s (%.1f MB)", dest, dest.stat().st_size / 1e6)

    @retry(max_attempts=3, backoff_base=5.0, exceptions=(requests.RequestException,))
    def _download(self, dest: Path) -> None:
        with requests.get(UCDP_GED_URL, stream=True, timeout=120) as resp:
            resp.raise_for_status()
            with open(dest, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=1 << 20):  # 1 MB chunks
                    fh.write(chunk)
