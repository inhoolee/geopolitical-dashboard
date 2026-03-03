"""ACLED extractor for local regional aggregate CSV snapshots."""

import logging
from pathlib import Path

from pipeline.config import ACLED_RAW_DIR, ACLED_REGIONAL_CSV_GLOB, ACLED_SUMMARY_CSV_PREFIX
from pipeline.extractors.base import BaseExtractor

logger = logging.getLogger(__name__)


class ACLEDExtractor(BaseExtractor):
    SOURCE_NAME = "ACLED"

    def _regional_csv_files(self) -> list[Path]:
        return [
            p
            for p in sorted(ACLED_RAW_DIR.glob(ACLED_REGIONAL_CSV_GLOB))
            if not p.name.startswith(ACLED_SUMMARY_CSV_PREFIX)
        ]

    def is_available(self) -> bool:
        files = self._regional_csv_files()
        if files:
            return True
        logger.warning(
            "ACLED unavailable. Expected local regional CSV snapshots in %s matching %s",
            ACLED_RAW_DIR,
            ACLED_REGIONAL_CSV_GLOB,
        )
        return False

    def extract(self, **kwargs) -> None:
        files = self._regional_csv_files()
        logger.info("ACLED local CSV mode: %d regional files found in %s", len(files), ACLED_RAW_DIR)
        for path in files:
            logger.debug("ACLED regional CSV: %s", path.name)
