"""Abstract base extractor with graceful degradation."""

import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseExtractor(ABC):
    SOURCE_NAME: str = "UNNAMED"

    def is_available(self) -> bool:
        """Override to gate on credentials or connectivity. Default: always available."""
        return True

    @abstractmethod
    def extract(self, **kwargs) -> None:
        """Pull raw data to data/raw/<source>/. Side-effects only."""
        ...

    def run(self, **kwargs) -> bool:
        """Check availability, then extract. Returns True on success."""
        if not self.is_available():
            logger.warning(
                "Skipping %s: not available (check credentials / config)",
                self.SOURCE_NAME,
            )
            return False
        self.extract(**kwargs)
        return True
