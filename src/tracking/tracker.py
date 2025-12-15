"""
Dataset tracking module.
Tracks which datasets have been processed to avoid duplicates.
Follows Single Responsibility Principle: Only handles tracking logic.
Uses simple Set-based tracking (KISS principle).
"""

from typing import Set

from src.utils.logger import get_logger


class Tracker:
    """
    Tracks processed datasets using an in-memory Set for O(1) lookups.
    Simple and efficient solution following KISS principle.
    """

    def __init__(self):
        """Initialize tracker with empty set."""
        self._processed_datasets: Set[str] = set()
        self.logger = get_logger(__name__)
        self.logger.info("Tracker initialized")

    def is_new_dataset(self, dataset_ref: str) -> bool:
        """
        Check if a dataset is new (not yet processed).

        Args:
            dataset_ref: Dataset reference (username/dataset-name)

        Returns:
            True if dataset has not been processed yet
        """
        return dataset_ref not in self._processed_datasets

    def mark_as_processed(self, dataset_ref: str) -> None:
        """
        Mark a dataset as processed.

        Args:
            dataset_ref: Dataset reference (username/dataset-name)
        """
        if dataset_ref in self._processed_datasets:
            self.logger.warning(f"Dataset already marked as processed: {dataset_ref}")
        else:
            self._processed_datasets.add(dataset_ref)
            self.logger.debug(f"Marked as processed: {dataset_ref}")

    def get_processed_count(self) -> int:
        """
        Get count of processed datasets.

        Returns:
            Number of datasets that have been processed
        """
        return len(self._processed_datasets)

    def get_all_processed(self) -> Set[str]:
        """
        Get set of all processed dataset references.

        Returns:
            Set of dataset references
        """
        return self._processed_datasets.copy()

    def load_processed(self, dataset_refs: Set[str]) -> None:
        """
        Load previously processed datasets (typically from state file).

        Args:
            dataset_refs: Set of dataset references to mark as processed
        """
        self._processed_datasets = dataset_refs.copy()
        self.logger.info(f"Loaded {len(dataset_refs)} processed datasets")

    def remove_processed(self, dataset_ref: str) -> bool:
        """
        Remove a dataset from the processed set.
        Useful if you need to reprocess a dataset.

        Args:
            dataset_ref: Dataset reference (username/dataset-name)

        Returns:
            True if dataset was removed, False if it wasn't in the set
        """
        if dataset_ref in self._processed_datasets:
            self._processed_datasets.remove(dataset_ref)
            self.logger.info(f"Removed from processed set: {dataset_ref}")
            return True
        else:
            self.logger.warning(f"Dataset not in processed set: {dataset_ref}")
            return False

    def clear(self) -> None:
        """Clear all tracked datasets."""
        count = len(self._processed_datasets)
        self._processed_datasets.clear()
        self.logger.info(f"Cleared {count} processed datasets from tracker")

    def get_statistics(self) -> dict:
        """
        Get tracking statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            'total_processed': len(self._processed_datasets),
            'sample_refs': list(self._processed_datasets)[:10]  # First 10 for preview
        }
