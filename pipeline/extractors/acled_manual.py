"""Extractor for the hand-maintained ACLED KPI backfill CSV."""

import logging

from pipeline.config import ACLED_MANUAL_KPI_BACKFILL_CSV
from pipeline.extractors.base import BaseExtractor

logger = logging.getLogger(__name__)


class ACLEDManualExtractor(BaseExtractor):
    SOURCE_NAME = "ACLED_MANUAL"

    def is_available(self) -> bool:
        available = ACLED_MANUAL_KPI_BACKFILL_CSV.exists()
        if not available:
            logger.warning("ACLED manual backfill CSV not found: %s", ACLED_MANUAL_KPI_BACKFILL_CSV)
        return available

    def extract(self, **kwargs) -> None:
        logger.info(
            "ACLED manual KPI backfill file ready: %s (%d bytes)",
            ACLED_MANUAL_KPI_BACKFILL_CSV,
            ACLED_MANUAL_KPI_BACKFILL_CSV.stat().st_size,
        )
