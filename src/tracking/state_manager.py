"""
State persistence manager.
Handles saving and loading tracking state to/from disk.
Follows Single Responsibility Principle: Only manages state persistence.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Set, Optional
import shutil

from src.utils.logger import get_logger


class StateManager:
    """
    Manages persistent state storage for tracker.
    Uses atomic writes to ensure data integrity.
    """

    def __init__(self, state_dir: Path):
        """
        Initialize state manager.

        Args:
            state_dir: Directory for storing state files
        """
        self.state_dir = Path(state_dir)
        self.state_file = self.state_dir / "tracking_state.json"
        self.backup_file = self.state_dir / "tracking_state.json.backup"
        self.logger = get_logger(__name__)

        # Ensure state directory exists
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"StateManager initialized with state dir: {self.state_dir}")

        # Statistics
        self.successful_downloads = 0
        self.failed_downloads = 0
        self.last_poll_timestamp: Optional[datetime] = None

    def save_state(
        self,
        processed_datasets: Set[str],
        successful_downloads: Optional[int] = None,
        failed_downloads: Optional[int] = None
    ) -> bool:
        """
        Save tracking state to disk using atomic write.
        Creates backup of previous state before writing.

        Args:
            processed_datasets: Set of processed dataset references
            successful_downloads: Count of successful downloads
            failed_downloads: Count of failed downloads

        Returns:
            True if successful, False otherwise
        """
        try:
            # Update statistics if provided
            if successful_downloads is not None:
                self.successful_downloads = successful_downloads
            if failed_downloads is not None:
                self.failed_downloads = failed_downloads

            # Create state data
            state_data = {
                'version': '1.0',
                'last_updated': datetime.now().isoformat(),
                'processed_datasets': sorted(list(processed_datasets)),
                'statistics': {
                    'total_processed': len(processed_datasets),
                    'last_poll_timestamp': self.last_poll_timestamp.isoformat() if self.last_poll_timestamp else None,
                    'successful_downloads': self.successful_downloads,
                    'failed_downloads': self.failed_downloads
                }
            }

            # Backup existing state file
            if self.state_file.exists():
                shutil.copy2(self.state_file, self.backup_file)

            # Write to temporary file
            temp_file = self.state_file.with_suffix('.json.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)

            # Atomic rename
            temp_file.replace(self.state_file)

            self.logger.debug(f"Saved state with {len(processed_datasets)} processed datasets")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")
            return False

    def load_state(self) -> Set[str]:
        """
        Load tracking state from disk.
        Falls back to backup if main state file is corrupted.

        Returns:
            Set of processed dataset references
        """
        # Try to load from main state file
        processed = self._load_from_file(self.state_file)
        if processed is not None:
            return processed

        # Try backup file
        self.logger.warning("Main state file failed, trying backup...")
        processed = self._load_from_file(self.backup_file)
        if processed is not None:
            # Restore backup as main file
            if self.backup_file.exists():
                shutil.copy2(self.backup_file, self.state_file)
            return processed

        # No valid state found
        self.logger.info("No valid state file found, starting with empty state")
        return set()

    def _load_from_file(self, file_path: Path) -> Optional[Set[str]]:
        """
        Load state from a specific file.

        Args:
            file_path: Path to state file

        Returns:
            Set of dataset references, or None if failed
        """
        try:
            if not file_path.exists():
                return None

            with open(file_path, 'r', encoding='utf-8') as f:
                state_data = json.load(f)

            # Extract processed datasets
            processed_list = state_data.get('processed_datasets', [])
            processed_set = set(processed_list)

            # Load statistics
            stats = state_data.get('statistics', {})
            self.successful_downloads = stats.get('successful_downloads', 0)
            self.failed_downloads = stats.get('failed_downloads', 0)

            last_poll = stats.get('last_poll_timestamp')
            if last_poll:
                try:
                    self.last_poll_timestamp = datetime.fromisoformat(last_poll)
                except Exception:
                    pass

            self.logger.info(
                f"Loaded state: {len(processed_set)} processed datasets, "
                f"{self.successful_downloads} successful, {self.failed_downloads} failed"
            )
            return processed_set

        except Exception as e:
            self.logger.error(f"Failed to load state from {file_path}: {e}")
            return None

    def backup_state(self) -> bool:
        """
        Create manual backup of current state.

        Returns:
            True if successful
        """
        try:
            if self.state_file.exists():
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = self.state_dir / f"tracking_state_{timestamp}.json.backup"
                shutil.copy2(self.state_file, backup_path)
                self.logger.info(f"Created manual backup: {backup_path.name}")
                return True
            return False

        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            return False

    def restore_from_backup(self) -> bool:
        """
        Restore state from backup file.

        Returns:
            True if successful
        """
        try:
            if self.backup_file.exists():
                shutil.copy2(self.backup_file, self.state_file)
                self.logger.info("Restored state from backup")
                return True
            else:
                self.logger.warning("No backup file found")
                return False

        except Exception as e:
            self.logger.error(f"Failed to restore from backup: {e}")
            return False

    def update_poll_timestamp(self) -> None:
        """Update the last poll timestamp to now."""
        self.last_poll_timestamp = datetime.now()

    def increment_successful_downloads(self, count: int = 1) -> None:
        """Increment successful downloads counter."""
        self.successful_downloads += count

    def increment_failed_downloads(self, count: int = 1) -> None:
        """Increment failed downloads counter."""
        self.failed_downloads += count

    def get_statistics(self) -> dict:
        """
        Get state management statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            'state_file_exists': self.state_file.exists(),
            'backup_file_exists': self.backup_file.exists(),
            'successful_downloads': self.successful_downloads,
            'failed_downloads': self.failed_downloads,
            'last_poll_timestamp': self.last_poll_timestamp.isoformat() if self.last_poll_timestamp else None
        }
