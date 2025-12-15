"""
Download service with retry logic.
Coordinates dataset downloads with error handling and retries.
Follows Single Responsibility Principle: Only handles download coordination.
Uses tenacity for exponential backoff retry logic.
"""

from pathlib import Path
from datetime import datetime

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from src.models.dataset import Dataset
from src.utils.logger import get_logger


class DownloadService:
    """
    Coordinates dataset downloads with automatic retry logic.
    Handles download validation and cleanup of failed downloads.
    """

    def __init__(self, kaggle_client, file_store, config):
        """
        Initialize download service.

        Args:
            kaggle_client: KaggleClient instance for API access
            file_store: FileStore instance for file management
            config: Settings configuration object
        """
        self.kaggle_client = kaggle_client
        self.file_store = file_store
        self.config = config
        self.logger = get_logger(__name__)

    def download(self, dataset: Dataset) -> bool:
        """
        Download dataset with retry logic and validation.
        This is the main entry point for downloads.

        Args:
            dataset: Dataset object to download

        Returns:
            True if download successful, False otherwise
        """
        try:
            self.logger.info(f"Starting download: {dataset.dataset_ref}")

            # Get download path
            download_path = self.file_store.get_dataset_path(dataset.dataset_ref)

            # Check if already exists
            if self.file_store.dataset_exists(dataset.dataset_ref):
                self.logger.info(f"Dataset already exists locally: {dataset.dataset_ref}")
                dataset.local_path = str(download_path)
                dataset.ingestion_status = "completed"
                return True

            # Check available disk space
            available_space = self.file_store.get_available_disk_space()
            if available_space != -1 and available_space < dataset.total_bytes * 2:
                self.logger.error(
                    f"Insufficient disk space for {dataset.dataset_ref}. "
                    f"Available: {available_space}, Required: ~{dataset.total_bytes * 2}"
                )
                dataset.ingestion_status = "failed"
                dataset.error_message = "Insufficient disk space"
                return False

            # Update dataset status
            dataset.ingestion_status = "downloading"
            dataset.ingestion_timestamp = datetime.now()

            # Download with retry
            success = self._download_with_retry(dataset.dataset_ref, download_path)

            if success:
                # Validate download
                if self.validate_download(download_path, dataset.total_bytes):
                    dataset.local_path = str(download_path)
                    dataset.ingestion_status = "completed"
                    self.logger.info(f"Successfully downloaded: {dataset.dataset_ref}")
                    return True
                else:
                    self.logger.error(f"Download validation failed: {dataset.dataset_ref}")
                    self.cleanup_failed_download(dataset.dataset_ref)
                    dataset.ingestion_status = "failed"
                    dataset.error_message = "Validation failed"
                    return False
            else:
                dataset.ingestion_status = "failed"
                dataset.error_message = "Download failed after retries"
                self.cleanup_failed_download(dataset.dataset_ref)
                return False

        except Exception as e:
            self.logger.error(f"Unexpected error downloading {dataset.dataset_ref}: {e}")
            dataset.ingestion_status = "failed"
            dataset.error_message = str(e)
            self.cleanup_failed_download(dataset.dataset_ref)
            return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=60),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, Exception)),
        reraise=False
    )
    def _download_with_retry(self, dataset_ref: str, download_path: Path) -> bool:
        """
        Download dataset with automatic retry on failure.
        Uses exponential backoff: 4s, 8s, 16s (capped at 60s).

        Args:
            dataset_ref: Dataset reference (username/dataset-name)
            download_path: Local path to download to

        Returns:
            True if successful, False otherwise

        Raises:
            Exception: On download failures (will be retried by tenacity)
        """
        try:
            return self.kaggle_client.download_dataset(
                dataset_ref=dataset_ref,
                download_path=download_path,
                unzip=True
            )
        except Exception as e:
            self.logger.warning(f"Download attempt failed for {dataset_ref}: {e}")
            raise

    def validate_download(self, path: Path, expected_size: int) -> bool:
        """
        Validate that download was successful.

        Args:
            path: Path to downloaded dataset
            expected_size: Expected total size in bytes

        Returns:
            True if validation passes
        """
        try:
            if not path.exists():
                self.logger.error(f"Download path does not exist: {path}")
                return False

            # Check if directory contains files
            if not any(path.iterdir()):
                self.logger.error(f"Download directory is empty: {path}")
                return False

            # Optional: Check size (allow some variance for compression)
            # actual_size = self.file_store.get_dataset_size(path.name)
            # size_diff = abs(actual_size - expected_size) / expected_size
            # if size_diff > 0.2:  # Allow 20% variance
            #     self.logger.warning(f"Size mismatch: expected {expected_size}, got {actual_size}")

            return True

        except Exception as e:
            self.logger.error(f"Validation error for {path}: {e}")
            return False

    def cleanup_failed_download(self, dataset_ref: str) -> None:
        """
        Clean up partial/failed download files.

        Args:
            dataset_ref: Dataset reference (username/dataset-name)
        """
        try:
            self.file_store.cleanup_failed_downloads(dataset_ref)
            self.logger.info(f"Cleaned up failed download: {dataset_ref}")
        except Exception as e:
            self.logger.error(f"Failed to cleanup {dataset_ref}: {e}")

    def get_download_progress(self, dataset_ref: str) -> dict:
        """
        Get download progress information.

        Args:
            dataset_ref: Dataset reference (username/dataset-name)

        Returns:
            Dictionary with progress information
        """
        exists = self.file_store.dataset_exists(dataset_ref)
        size = self.file_store.get_dataset_size(dataset_ref) if exists else 0

        return {
            'dataset_ref': dataset_ref,
            'exists': exists,
            'size_bytes': size,
            'size_mb': round(size / (1024 * 1024), 2)
        }
