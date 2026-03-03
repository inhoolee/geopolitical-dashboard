"""Seed events extractor – reads the hand-curated diplomatic events CSV."""

import logging

from pipeline.config import DIPLOMATIC_SEED_CSV
from pipeline.extractors.base import BaseExtractor

logger = logging.getLogger(__name__)


class SeedEventsExtractor(BaseExtractor):
    SOURCE_NAME = "SEED"

    def is_available(self) -> bool:
        available = DIPLOMATIC_SEED_CSV.exists()
        if not available:
            logger.warning("Seed CSV not found: %s", DIPLOMATIC_SEED_CSV)
        return available

    def extract(self, **kwargs) -> None:
        # No download needed – file is already local (checked into git)
        logger.info("Seed events file ready: %s (%d bytes)",
                    DIPLOMATIC_SEED_CSV, DIPLOMATIC_SEED_CSV.stat().st_size)
