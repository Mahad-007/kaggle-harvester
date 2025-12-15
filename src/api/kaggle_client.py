"""
Kaggle API client wrapper.
Handles all interactions with the Kaggle API.
Follows Single Responsibility Principle: Only manages Kaggle API communication.
Follows Dependency Inversion: Depends on KaggleConfig abstraction.
"""

import logging
import os
from pathlib import Path
from typing import List, Optional

from src.api.base_client import BaseAPIClient
from src.models.dataset import Dataset
from src.utils.logger import get_logger


class KaggleClient(BaseAPIClient):
    """
    Wrapper for Kaggle API with authentication and dataset operations.
    Provides a clean interface for listing and downloading datasets.
    """

    def __init__(self, kaggle_config):
        """
        Initialize Kaggle API client.

        Args:
            kaggle_config: KaggleConfig instance with API credentials
        """
        self.config = kaggle_config
        self.api = None  # Will be initialized during authentication
        self.logger = get_logger(__name__)
        self._authenticated = False

    def authenticate(self) -> None:
        """
        Authenticate with Kaggle API using provided credentials.

        Raises:
            ValueError: If credentials are invalid
            Exception: If authentication fails
        """
        if self._authenticated:
            self.logger.debug("Already authenticated with Kaggle API")
            return

        # Set environment variables for Kaggle API
        if self.config.username and self.config.key:
            os.environ['KAGGLE_USERNAME'] = self.config.username
            os.environ['KAGGLE_KEY'] = self.config.key

        try:
            # Import here to avoid authentication on module import
            from kaggle.api.kaggle_api_extended import KaggleApi
            self.api = KaggleApi()
            self.api.authenticate()
            self._authenticated = True
            self.logger.info("Successfully authenticated with Kaggle API")
        except Exception as e:
            self.logger.error(f"Failed to authenticate with Kaggle API: {e}")
            raise ValueError(
                "Kaggle API authentication failed. "
                "Please check your KAGGLE_USERNAME and KAGGLE_KEY credentials."
            ) from e

    def list_recent_datasets(
        self,
        max_size: int = 100,
        page: int = 1
    ) -> List[Dataset]:
        """
        List recent datasets from Kaggle sorted by last updated.

        Args:
            max_size: Maximum number of datasets to retrieve (1-100)
            page: Page number for pagination

        Returns:
            List of Dataset objects

        Raises:
            ValueError: If not authenticated or parameters invalid
            Exception: If API call fails
        """
        if not self._authenticated:
            raise ValueError("Must authenticate before listing datasets")

        if max_size < 1 or max_size > 100:
            raise ValueError("max_size must be between 1 and 100")

        try:
            self.logger.debug(f"Fetching datasets (page={page}, max_size={max_size})")

            # Fetch datasets from Kaggle API
            api_datasets = self.api.dataset_list(
                sort_by=self.config.sort_by,
                page=page,
                max_size=max_size
            )

            # Convert to our Dataset model
            datasets = []
            for api_dataset in api_datasets:
                try:
                    dataset = Dataset.from_kaggle_api(api_dataset)
                    datasets.append(dataset)
                except Exception as e:
                    self.logger.warning(
                        f"Failed to parse dataset {getattr(api_dataset, 'ref', 'unknown')}: {e}"
                    )
                    continue

            self.logger.info(f"Successfully fetched {len(datasets)} datasets from Kaggle API")
            return datasets

        except Exception as e:
            self.logger.error(f"Failed to list datasets: {e}")
            raise

    def download_dataset(
        self,
        dataset_ref: str,
        download_path: Path,
        unzip: bool = True
    ) -> bool:
        """
        Download dataset files from Kaggle.

        Args:
            dataset_ref: Dataset reference (username/dataset-name)
            download_path: Local directory to download files to
            unzip: Whether to automatically extract compressed files

        Returns:
            True if download successful, False otherwise

        Raises:
            ValueError: If not authenticated
        """
        if not self._authenticated:
            raise ValueError("Must authenticate before downloading datasets")

        try:
            self.logger.info(f"Downloading dataset: {dataset_ref}")

            # Ensure download path exists
            download_path.mkdir(parents=True, exist_ok=True)

            # Download using Kaggle API
            self.api.dataset_download_files(
                dataset=dataset_ref,
                path=str(download_path),
                unzip=unzip,
                quiet=False
            )

            self.logger.info(f"Successfully downloaded dataset: {dataset_ref}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to download dataset {dataset_ref}: {e}")
            return False

    def get_dataset_metadata(self, dataset_ref: str) -> Optional[dict]:
        """
        Get detailed metadata for a specific dataset.

        Args:
            dataset_ref: Dataset reference (username/dataset-name)

        Returns:
            Dictionary with dataset metadata, or None if failed

        Raises:
            ValueError: If not authenticated
        """
        if not self._authenticated:
            raise ValueError("Must authenticate before getting metadata")

        try:
            self.logger.debug(f"Fetching metadata for dataset: {dataset_ref}")

            metadata = self.api.dataset_metadata(dataset=dataset_ref)

            self.logger.debug(f"Successfully fetched metadata for: {dataset_ref}")
            return metadata

        except Exception as e:
            self.logger.warning(f"Failed to fetch metadata for {dataset_ref}: {e}")
            return None

    def dataset_exists(self, dataset_ref: str) -> bool:
        """
        Check if a dataset exists on Kaggle.

        Args:
            dataset_ref: Dataset reference (username/dataset-name)

        Returns:
            True if dataset exists, False otherwise
        """
        try:
            metadata = self.get_dataset_metadata(dataset_ref)
            return metadata is not None
        except Exception:
            return False

    def get_platform_name(self) -> str:
        """
        Return the platform name.

        Returns:
            Platform name 'kaggle'
        """
        return "kaggle"
