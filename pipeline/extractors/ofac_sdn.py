"""OFAC Specially Designated Nationals (SDN) list extractor."""

import logging
from pathlib import Path

import requests

from pipeline.config import OFAC_SDN_URL, OFAC_RAW_DIR
from pipeline.extractors.base import BaseExtractor
from pipeline.utils.retry import retry

logger = logging.getLogger(__name__)

SDN_FILENAME = "sdn.csv"


class OFACSDNExtractor(BaseExtractor):
    SOURCE_NAME = "OFAC_SDN"

    def extract(self, force: bool = False, **kwargs) -> None:
        OFAC_RAW_DIR.mkdir(parents=True, exist_ok=True)
        dest = OFAC_RAW_DIR / SDN_FILENAME

        if dest.exists() and not force:
            logger.info("OFAC SDN already present – skipping (use force=True to refresh)")
            return

        logger.info("Downloading OFAC SDN list from %s", OFAC_SDN_URL)
        self._download(dest)
        logger.info("OFAC SDN download complete: %s", dest)

    @retry(max_attempts=3, backoff_base=3.0, exceptions=(requests.RequestException,))
    def _download(self, dest: Path) -> None:
        with requests.get(OFAC_SDN_URL, stream=True, timeout=60) as resp:
            resp.raise_for_status()
            with open(dest, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=512 * 1024):
                    fh.write(chunk)
