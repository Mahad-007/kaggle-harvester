"""
File storage management.
Handles all file system operations for dataset storage.
Follows Single Responsibility Principle: Only manages file operations.
Follows DRY Principle: Centralizes all file operations.
"""

import shutil
from pathlib import Path
from typing import Optional
import os

from src.utils.logger import get_logger


class FileStore:
    """
    Manages dataset file storage on the local file system.
    Provides atomic operations for file management.
    """

    def __init__(self, base_path: Path):
        """
        Initialize file store.

        Args:
            base_path: Base directory for storing datasets
        """
        self.base_path = Path(base_path)
        self.logger = get_logger(__name__)

        # Ensure base directory exists
        self.ensure_directory_exists(self.base_path)
        self.logger.info(f"FileStore initialized with base path: {self.base_path}")

    def ensure_directory_exists(self, path: Path) -> None:
        """
        Create directory if it doesn't exist.

        Args:
            path: Directory path to create
        """
        path.mkdir(parents=True, exist_ok=True)

    def get_dataset_path(self, dataset_ref: str) -> Path:
        """
        Generate consistent path for a dataset.
        Format: base_path/username/dataset-name/

        Args:
            dataset_ref: Dataset reference (username/dataset-name)

        Returns:
            Path object for dataset directory
        """
        parts = dataset_ref.split('/')
        if len(parts) != 2:
            raise ValueError(f"Invalid dataset reference format: {dataset_ref}")

        username, dataset_name = parts
        return self.base_path / username / dataset_name

    def dataset_exists(self, dataset_ref: str) -> bool:
        """
        Check if dataset files exist locally.

        Args:
            dataset_ref: Dataset reference (username/dataset-name)

        Returns:
            True if dataset directory exists and contains files
        """
        dataset_path = self.get_dataset_path(dataset_ref)
        if not dataset_path.exists():
            return False

        # Check if directory contains any files
        return any(dataset_path.iterdir())

    def save_file(self, source: Path, destination: Path) -> bool:
        """
        Save a file to the destination path.

        Args:
            source: Source file path
            destination: Destination file path

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure destination directory exists
            destination.parent.mkdir(parents=True, exist_ok=True)

            # Copy file
            shutil.copy2(source, destination)
            self.logger.debug(f"Saved file: {destination}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save file {destination}: {e}")
            return False

    def file_exists(self, path: Path) -> bool:
        """
        Check if a file exists.

        Args:
            path: File path to check

        Returns:
            True if file exists
        """
        return Path(path).exists() and Path(path).is_file()

    def get_available_disk_space(self) -> int:
        """
        Get available disk space in bytes.

        Returns:
            Available disk space in bytes
        """
        try:
            stat = os.statvfs(str(self.base_path))
            available_bytes = stat.f_bavail * stat.f_frsize
            return available_bytes
        except Exception as e:
            self.logger.warning(f"Failed to get disk space: {e}")
            return -1

    def cleanup_failed_downloads(self, dataset_ref: str) -> bool:
        """
        Remove partial/failed download files for a dataset.

        Args:
            dataset_ref: Dataset reference (username/dataset-name)

        Returns:
            True if cleanup successful
        """
        try:
            dataset_path = self.get_dataset_path(dataset_ref)
            if dataset_path.exists():
                shutil.rmtree(dataset_path)
                self.logger.info(f"Cleaned up failed download: {dataset_ref}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to cleanup {dataset_ref}: {e}")
            return False

    def get_dataset_size(self, dataset_ref: str) -> int:
        """
        Calculate total size of downloaded dataset.

        Args:
            dataset_ref: Dataset reference (username/dataset-name)

        Returns:
            Total size in bytes, or 0 if dataset doesn't exist
        """
        dataset_path = self.get_dataset_path(dataset_ref)
        if not dataset_path.exists():
            return 0

        total_size = 0
        try:
            for file_path in dataset_path.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except Exception as e:
            self.logger.warning(f"Failed to calculate size for {dataset_ref}: {e}")

        return total_size

    def list_downloaded_datasets(self) -> list:
        """
        List all downloaded datasets.

        Returns:
            List of dataset references (username/dataset-name)
        """
        datasets = []
        try:
            # Iterate through username directories
            for username_dir in self.base_path.iterdir():
                if not username_dir.is_dir():
                    continue

                # Iterate through dataset directories
                for dataset_dir in username_dir.iterdir():
                    if not dataset_dir.is_dir():
                        continue

                    dataset_ref = f"{username_dir.name}/{dataset_dir.name}"
                    datasets.append(dataset_ref)

        except Exception as e:
            self.logger.error(f"Failed to list downloaded datasets: {e}")

        return datasets

    def get_statistics(self) -> dict:
        """
        Get storage statistics.

        Returns:
            Dictionary with storage statistics
        """
        downloaded_datasets = self.list_downloaded_datasets()
        total_size = sum(
            self.get_dataset_size(ref) for ref in downloaded_datasets
        )

        return {
            'total_datasets': len(downloaded_datasets),
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'total_size_gb': round(total_size / (1024 * 1024 * 1024), 2),
            'available_space_bytes': self.get_available_disk_space(),
            'base_path': str(self.base_path)
        }
