"""
Platform factory for creating appropriate API clients and ingestion services.
Follows Factory Pattern and Open/Closed Principle.
Encapsulates platform selection logic in a single place.
"""

from src.api.base_client import BaseAPIClient
from src.api.kaggle_client import KaggleClient
from src.api.huggingface_client import HuggingFaceClient
from src.utils.logger import get_logger


class PlatformFactory:
    """
    Factory for creating platform-specific API clients.
    Centralizes platform selection and client instantiation.
    """

    @staticmethod
    def create_client(settings) -> BaseAPIClient:
        """
        Create appropriate API client based on platform setting.

        Args:
            settings: Settings object with platform configuration

        Returns:
            Platform-specific API client (KaggleClient or HuggingFaceClient)

        Raises:
            ValueError: If platform is not supported
        """
        logger = get_logger(__name__)
        platform = settings.platform.active.lower()

        logger.info(f"Creating API client for platform: {platform}")

        if platform == "kaggle":
            return KaggleClient(settings.kaggle)
        elif platform == "huggingface":
            return HuggingFaceClient(settings.huggingface)
        else:
            raise ValueError(
                f"Unsupported platform: {platform}. "
                f"Supported platforms: kaggle, huggingface"
            )

    @staticmethod
    def get_max_datasets_per_poll(settings) -> int:
        """
        Get max datasets per poll for active platform.

        Args:
            settings: Settings object with platform configuration

        Returns:
            Maximum datasets per poll for the active platform
        """
        platform = settings.platform.active.lower()
        if platform == "kaggle":
            return settings.kaggle.max_datasets_per_poll
        elif platform == "huggingface":
            return settings.huggingface.max_datasets_per_poll
        else:
            return 100  # Default fallback
