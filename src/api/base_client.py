"""
Abstract base class for platform API clients.
Defines interface that all platform clients must implement.
Follows Interface Segregation Principle and Dependency Inversion Principle.
"""

from abc import ABC, abstractmethod
from typing import List
from pathlib import Path
from src.models.dataset import Dataset


class BaseAPIClient(ABC):
    """
    Abstract base class for platform API clients.
    All platform-specific clients must implement these methods.
    """

    @abstractmethod
    def authenticate(self) -> None:
        """
        Authenticate with the platform API.

        Raises:
            ValueError: If authentication fails
            Exception: For other authentication errors
        """
        pass

    @abstractmethod
    def list_recent_datasets(self, max_size: int, page: int) -> List[Dataset]:
        """
        List recent datasets from the platform.

        Args:
            max_size: Maximum number of datasets to retrieve
            page: Page number for pagination

        Returns:
            List of Dataset objects

        Raises:
            ValueError: If not authenticated or parameters invalid
            Exception: If API call fails
        """
        pass

    @abstractmethod
    def download_dataset(
        self,
        dataset_ref: str,
        download_path: Path,
        unzip: bool = True
    ) -> bool:
        """
        Download dataset files from the platform.

        Args:
            dataset_ref: Dataset reference (username/dataset-name)
            download_path: Local directory to download files to
            unzip: Whether to automatically extract compressed files

        Returns:
            True if download successful, False otherwise

        Raises:
            ValueError: If not authenticated
        """
        pass

    @abstractmethod
    def get_platform_name(self) -> str:
        """
        Return the platform name.

        Returns:
            Platform name (e.g., 'kaggle', 'huggingface')
        """
        pass
