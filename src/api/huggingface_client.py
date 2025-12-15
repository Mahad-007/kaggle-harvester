"""
Hugging Face API client wrapper.
Handles all interactions with the Hugging Face Hub API.
Follows Single Responsibility Principle: Only manages Hugging Face API communication.
Follows Dependency Inversion: Depends on HuggingFaceConfig abstraction.
"""

import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta

from src.api.base_client import BaseAPIClient
from src.models.dataset import Dataset
from src.utils.logger import get_logger


class HuggingFaceClient(BaseAPIClient):
    """
    Wrapper for Hugging Face Hub API with authentication and dataset operations.
    Approximates "trending" by combining downloads and recency.
    """

    def __init__(self, hf_config):
        """
        Initialize Hugging Face API client.

        Args:
            hf_config: HuggingFaceConfig instance with API settings
        """
        self.config = hf_config
        self.api = None  # Will be initialized during authentication
        self.logger = get_logger(__name__)
        self._authenticated = False

    def authenticate(self) -> None:
        """
        Authenticate with Hugging Face API using token (optional for public datasets).

        Raises:
            ValueError: If API initialization fails
            Exception: If authentication fails
        """
        if self._authenticated:
            self.logger.debug("Already authenticated with Hugging Face API")
            return

        try:
            from huggingface_hub import HfApi
            self.api = HfApi(token=self.config.token)

            # Test authentication if token provided
            if self.config.token:
                # This will raise an error if token is invalid
                self.api.whoami()
                self.logger.info("Successfully authenticated with Hugging Face API (with token)")
            else:
                self.logger.info("Using Hugging Face API without authentication (public datasets only)")

            self._authenticated = True

        except Exception as e:
            self.logger.error(f"Failed to initialize Hugging Face API: {e}")
            raise ValueError(
                "Hugging Face API initialization failed. "
                "Check your HF_TOKEN if accessing private datasets."
            ) from e

    def list_recent_datasets(
        self,
        max_size: int = 100,
        page: int = 1
    ) -> List[Dataset]:
        """
        List trending datasets from Hugging Face.

        Strategy: Fetch datasets sorted by downloads/lastModified,
        then filter client-side for recency and minimum popularity.

        Args:
            max_size: Maximum number of datasets to retrieve
            page: Page number (not used due to client-side filtering)

        Returns:
            List of Dataset objects approximating "trending"

        Raises:
            ValueError: If not authenticated
            Exception: If API call fails
        """
        if not self._authenticated:
            raise ValueError("Must authenticate before listing datasets")

        try:
            self.logger.debug(f"Fetching Hugging Face datasets (max={max_size})")

            # Calculate recency threshold
            cutoff_date = datetime.now(tz=None) - timedelta(days=self.config.recency_filter_days)

            # Fetch MORE datasets than needed because we'll filter client-side
            # Multiply by 10 to account for filtering
            fetch_limit = max_size * 10

            # Strategy depends on config
            if self.config.trending_approximation_method == "downloads_with_recency":
                # Fetch by downloads, filter by recency
                api_datasets = self.api.list_datasets(
                    sort="downloads",
                    direction=-1,
                    limit=fetch_limit,
                    full=True  # Get complete info including last_modified
                )
            elif self.config.trending_approximation_method == "recent_popular":
                # Fetch by lastModified, filter by downloads
                api_datasets = self.api.list_datasets(
                    sort="lastModified",
                    direction=-1,
                    limit=fetch_limit,
                    full=True
                )
            else:
                # Default: sort by downloads
                api_datasets = self.api.list_datasets(
                    sort="downloads",
                    direction=-1,
                    limit=fetch_limit,
                    full=True
                )

            # Convert and filter
            trending_datasets = []
            for api_dataset in api_datasets:
                try:
                    # Filter by recency
                    if api_dataset.last_modified:
                        # Remove timezone info for comparison
                        last_modified = api_dataset.last_modified.replace(tzinfo=None)
                        if last_modified < cutoff_date:
                            continue
                    else:
                        # Skip datasets without last_modified info
                        continue

                    # Filter by minimum downloads (popularity threshold)
                    if (api_dataset.downloads or 0) < self.config.min_downloads_threshold:
                        continue

                    # Convert to our Dataset model
                    dataset = Dataset.from_huggingface_api(api_dataset)
                    trending_datasets.append(dataset)

                    # Stop once we have enough
                    if len(trending_datasets) >= max_size:
                        break

                except Exception as e:
                    self.logger.warning(
                        f"Failed to parse dataset {getattr(api_dataset, 'id', 'unknown')}: {e}"
                    )
                    continue

            self.logger.info(
                f"Found {len(trending_datasets)} trending datasets from Hugging Face "
                f"(filtered from {fetch_limit} total)"
            )
            return trending_datasets

        except Exception as e:
            self.logger.error(f"Failed to list Hugging Face datasets: {e}")
            raise

    def download_dataset(
        self,
        dataset_ref: str,
        download_path: Path,
        unzip: bool = True  # Ignored for HuggingFace
    ) -> bool:
        """
        Download dataset files from Hugging Face Hub.

        Note: HuggingFace datasets are more complex than Kaggle.
        This downloads the entire repository snapshot.

        Args:
            dataset_ref: Dataset reference (username/dataset-name)
            download_path: Local directory to download to
            unzip: Ignored (HuggingFace uses different format)

        Returns:
            True if download successful, False otherwise

        Raises:
            ValueError: If not authenticated
        """
        if not self._authenticated:
            raise ValueError("Must authenticate before downloading datasets")

        try:
            self.logger.info(f"Downloading Hugging Face dataset: {dataset_ref}")

            # Ensure download path exists
            download_path.mkdir(parents=True, exist_ok=True)

            # Download using HuggingFace snapshot_download
            from huggingface_hub import snapshot_download

            snapshot_download(
                repo_id=dataset_ref,
                repo_type="dataset",
                local_dir=str(download_path),
                token=self.config.token
            )

            self.logger.info(f"Successfully downloaded dataset: {dataset_ref}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to download dataset {dataset_ref}: {e}")
            return False

    def get_platform_name(self) -> str:
        """
        Return the platform name.

        Returns:
            Platform name 'huggingface'
        """
        return "huggingface"
