"""
Metadata storage management.
Handles JSON metadata file operations.
Follows Single Responsibility Principle: Only manages metadata storage.
Follows DRY Principle: Centralizes JSON operations.
"""

import json
from pathlib import Path
from typing import Optional, List, Dict

from src.models.dataset import Dataset
from src.utils.logger import get_logger


class MetadataStore:
    """
    Manages dataset metadata storage as JSON files.
    Provides atomic operations for metadata management.
    """

    def __init__(self, base_path: Path):
        """
        Initialize metadata store.

        Args:
            base_path: Base directory for storing metadata JSON files
        """
        self.base_path = Path(base_path)
        self.logger = get_logger(__name__)

        # Ensure base directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"MetadataStore initialized with base path: {self.base_path}")

    def _get_metadata_filename(self, dataset_ref: str, platform: str = "kaggle") -> str:
        """
        Generate consistent filename for metadata.
        Format: platform_username__dataset-name.json

        Args:
            dataset_ref: Dataset reference (username/dataset-name)
            platform: Platform name (kaggle or huggingface)

        Returns:
            Metadata filename
        """
        # Replace / with __ to create flat file structure
        # Include platform to prevent collisions
        safe_ref = dataset_ref.replace('/', '__')
        filename = f"{platform}_{safe_ref}.json"
        return filename

    def _get_metadata_path(self, dataset_ref: str, platform: str = "kaggle") -> Path:
        """
        Get full path for metadata file.

        Args:
            dataset_ref: Dataset reference (username/dataset-name)
            platform: Platform name (kaggle or huggingface)

        Returns:
            Path to metadata file
        """
        filename = self._get_metadata_filename(dataset_ref, platform)
        return self.base_path / filename

    def save_metadata(self, dataset: Dataset) -> bool:
        """
        Save dataset metadata as JSON file.
        Uses atomic write (write to temp file, then rename).

        Args:
            dataset: Dataset object to save

        Returns:
            True if successful, False otherwise
        """
        try:
            metadata_path = self._get_metadata_path(dataset.dataset_ref, dataset.platform)
            temp_path = metadata_path.with_suffix('.json.tmp')

            # Convert dataset to dictionary
            metadata_dict = dataset.to_dict()

            # Write to temporary file
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(metadata_dict, f, indent=2, ensure_ascii=False)

            # Atomic rename
            temp_path.replace(metadata_path)

            self.logger.debug(f"Saved metadata: {dataset.dataset_ref}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save metadata for {dataset.dataset_ref}: {e}")
            # Cleanup temp file if it exists
            if temp_path.exists():
                temp_path.unlink()
            return False

    def load_metadata(self, dataset_ref: str) -> Optional[Dict]:
        """
        Load metadata from JSON file.

        Args:
            dataset_ref: Dataset reference (username/dataset-name)

        Returns:
            Metadata dictionary, or None if not found
        """
        try:
            metadata_path = self._get_metadata_path(dataset_ref)

            if not metadata_path.exists():
                return None

            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            return metadata

        except Exception as e:
            self.logger.error(f"Failed to load metadata for {dataset_ref}: {e}")
            return None

    def metadata_exists(self, dataset_ref: str) -> bool:
        """
        Check if metadata file exists for a dataset.

        Args:
            dataset_ref: Dataset reference (username/dataset-name)

        Returns:
            True if metadata file exists
        """
        metadata_path = self._get_metadata_path(dataset_ref)
        return metadata_path.exists()

    def delete_metadata(self, dataset_ref: str) -> bool:
        """
        Delete metadata file for a dataset.

        Args:
            dataset_ref: Dataset reference (username/dataset-name)

        Returns:
            True if successful
        """
        try:
            metadata_path = self._get_metadata_path(dataset_ref)

            if metadata_path.exists():
                metadata_path.unlink()
                self.logger.info(f"Deleted metadata: {dataset_ref}")

            return True

        except Exception as e:
            self.logger.error(f"Failed to delete metadata for {dataset_ref}: {e}")
            return False

    def get_all_metadata(self) -> List[Dict]:
        """
        Load all metadata files.

        Returns:
            List of metadata dictionaries
        """
        all_metadata = []

        try:
            for metadata_file in self.base_path.glob('*.json'):
                # Skip temporary files
                if metadata_file.suffix == '.tmp':
                    continue

                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                        all_metadata.append(metadata)
                except Exception as e:
                    self.logger.warning(f"Failed to load {metadata_file.name}: {e}")

        except Exception as e:
            self.logger.error(f"Failed to get all metadata: {e}")

        return all_metadata

    def create_metadata_index(self) -> Dict[str, Dict]:
        """
        Create an index of all metadata keyed by dataset_ref.

        Returns:
            Dictionary mapping dataset_ref to metadata
        """
        index = {}
        all_metadata = self.get_all_metadata()

        for metadata in all_metadata:
            if 'dataset_ref' in metadata:
                index[metadata['dataset_ref']] = metadata

        return index

    def get_statistics(self) -> dict:
        """
        Get metadata storage statistics.

        Returns:
            Dictionary with statistics
        """
        metadata_files = list(self.base_path.glob('*.json'))
        total_size = sum(f.stat().st_size for f in metadata_files if f.exists())

        return {
            'total_metadata_files': len(metadata_files),
            'total_size_bytes': total_size,
            'total_size_kb': round(total_size / 1024, 2),
            'base_path': str(self.base_path)
        }
