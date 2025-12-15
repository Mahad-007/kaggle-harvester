"""
Main ingestion service orchestrator.
Coordinates the entire data ingestion workflow.
Follows Single Responsibility Principle: Only orchestrates, delegates actual work.
Follows Dependency Inversion: Depends on abstractions, not concrete implementations.
Follows Open/Closed Principle: Extensible via dependency injection.
"""

import signal
import sys
import time
from datetime import datetime

from src.api.kaggle_client import KaggleClient
from src.api.rate_limiter import RateLimiter
from src.storage.file_store import FileStore
from src.storage.metadata_store import MetadataStore
from src.tracking.tracker import Tracker
from src.tracking.state_manager import StateManager
from src.services.download_service import DownloadService
from src.utils.logger import get_logger


class IngestionService:
    """
    Main orchestrator for the Kaggle data ingestion engine.
    Coordinates polling, tracking, downloading, and metadata storage.
    """

    def __init__(self, settings):
        """
        Initialize ingestion service with all dependencies.
        Uses dependency injection following SOLID principles.

        Args:
            settings: Settings configuration object
        """
        self.settings = settings
        self.logger = get_logger(__name__)
        self.running = False
        self.poll_count = 0

        # Initialize all components (Dependency Injection)
        self.logger.info("Initializing ingestion service components...")

        self.kaggle_client = KaggleClient(settings.kaggle)
        self.rate_limiter = RateLimiter(settings.rate_limit.min_request_interval_seconds)
        self.tracker = Tracker()
        self.state_manager = StateManager(settings.storage.state_dir)
        self.file_store = FileStore(settings.storage.datasets_dir)
        self.metadata_store = MetadataStore(settings.storage.metadata_dir)
        self.download_service = DownloadService(
            self.kaggle_client,
            self.file_store,
            settings
        )

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._shutdown_handler)
        signal.signal(signal.SIGTERM, self._shutdown_handler)

        # Load previous state
        self._load_state()

        self.logger.info("Ingestion service initialized successfully")

    def _load_state(self) -> None:
        """Load previous tracking state from disk."""
        try:
            processed = self.state_manager.load_state()
            self.tracker.load_processed(processed)
            self.logger.info(f"Loaded {len(processed)} previously processed datasets")
        except Exception as e:
            self.logger.error(f"Failed to load state: {e}")
            self.logger.info("Starting with empty tracking state")

    def start(self) -> None:
        """
        Start the continuous polling service.
        Main entry point for the ingestion engine.
        """
        self.running = True
        self.logger.info("Starting Kaggle data ingestion service...")

        # Authenticate with Kaggle API
        try:
            self.kaggle_client.authenticate()
        except Exception as e:
            self.logger.critical(f"Failed to authenticate with Kaggle API: {e}")
            sys.exit(1)

        # Main polling loop
        while self.running:
            try:
                self.poll_count += 1
                self.logger.info(f"=== Starting poll cycle #{self.poll_count} ===")

                # Execute one poll cycle
                new_count = self.poll_once()

                self.logger.info(
                    f"=== Poll cycle #{self.poll_count} complete: "
                    f"{new_count} new datasets processed ==="
                )

                # Update state after successful poll
                self.state_manager.update_poll_timestamp()
                self._save_state()

            except KeyboardInterrupt:
                self.logger.info("Received keyboard interrupt")
                break
            except Exception as e:
                self.logger.error(f"Error in poll cycle #{self.poll_count}: {e}", exc_info=True)
                # Wait before retrying on error
                self.logger.info("Waiting 60 seconds before retrying...")
                time.sleep(60)
                continue

            # Wait for next poll interval (with shutdown checks)
            self._wait_for_next_poll()

        self.logger.info("Shutting down ingestion service...")
        self._shutdown()

    def poll_once(self) -> int:
        """
        Execute a single poll cycle.
        Fetches datasets, filters new ones, and processes them.

        Returns:
            Number of new datasets processed
        """
        try:
            # Rate limit before API call
            self.rate_limiter.wait_if_needed()

            # Fetch recent datasets from Kaggle
            self.logger.info("Fetching recent datasets from Kaggle API...")
            datasets = self.kaggle_client.list_recent_datasets(
                max_size=self.settings.kaggle.max_datasets_per_poll
            )

            self.logger.info(f"Fetched {len(datasets)} datasets from Kaggle API")

            # Filter new datasets
            new_datasets = [d for d in datasets if self.tracker.is_new_dataset(d.dataset_ref)]

            if not new_datasets:
                self.logger.info("No new datasets found")
                return 0

            self.logger.info(f"Found {len(new_datasets)} new datasets to process")

            # Process each new dataset
            successful = 0
            failed = 0

            for idx, dataset in enumerate(new_datasets, 1):
                self.logger.info(f"Processing dataset {idx}/{len(new_datasets)}: {dataset.dataset_ref}")

                try:
                    success = self._process_dataset(dataset)
                    if success:
                        successful += 1
                    else:
                        failed += 1

                except Exception as e:
                    self.logger.error(f"Failed to process {dataset.dataset_ref}: {e}")
                    failed += 1
                    continue

            # Update statistics
            self.state_manager.increment_successful_downloads(successful)
            self.state_manager.increment_failed_downloads(failed)

            self.logger.info(
                f"Processing complete: {successful} successful, {failed} failed"
            )

            return len(new_datasets)

        except Exception as e:
            self.logger.error(f"Error in poll_once: {e}")
            raise

    def _process_dataset(self, dataset) -> bool:
        """
        Process a single dataset: download, save metadata, and mark as processed.

        Args:
            dataset: Dataset object to process

        Returns:
            True if successful, False otherwise
        """
        try:
            # Download dataset files
            self.logger.info(f"Downloading dataset: {dataset.dataset_ref}")
            success = self.download_service.download(dataset)

            if not success:
                self.logger.error(f"Download failed: {dataset.dataset_ref}")
                # Still mark as processed to avoid retry loops
                self.tracker.mark_as_processed(dataset.dataset_ref)
                return False

            # Save metadata
            self.logger.info(f"Saving metadata: {dataset.dataset_ref}")
            metadata_success = self.metadata_store.save_metadata(dataset)

            if not metadata_success:
                self.logger.warning(f"Failed to save metadata: {dataset.dataset_ref}")

            # Mark as processed
            self.tracker.mark_as_processed(dataset.dataset_ref)

            self.logger.info(f"Successfully processed: {dataset.dataset_ref}")
            return True

        except Exception as e:
            self.logger.error(f"Error processing {dataset.dataset_ref}: {e}")
            # Mark as processed to avoid infinite retry
            self.tracker.mark_as_processed(dataset.dataset_ref)
            return False

    def _save_state(self) -> None:
        """Save current tracking state to disk."""
        try:
            self.state_manager.save_state(
                processed_datasets=self.tracker.get_all_processed(),
                successful_downloads=self.state_manager.successful_downloads,
                failed_downloads=self.state_manager.failed_downloads
            )
            self.logger.debug("State saved successfully")
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")

    def _wait_for_next_poll(self) -> None:
        """
        Wait for the next poll interval.
        Checks shutdown flag frequently to allow quick shutdown.
        """
        interval = self.settings.polling.interval_seconds
        self.logger.info(f"Waiting {interval} seconds until next poll...")

        # Check shutdown flag every second
        for _ in range(interval):
            if not self.running:
                break
            time.sleep(1)

    def _shutdown_handler(self, signum, frame) -> None:
        """
        Handle shutdown signals gracefully.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.running = False

    def _shutdown(self) -> None:
        """Perform cleanup before shutdown."""
        try:
            # Save final state
            self.logger.info("Saving final state...")
            self._save_state()

            # Log statistics
            stats = self.get_statistics()
            self.logger.info(f"Final statistics: {stats}")

            self.logger.info("Shutdown complete")

        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")

    def stop(self) -> None:
        """Stop the ingestion service gracefully."""
        self.logger.info("Stop requested...")
        self.running = False

    def get_statistics(self) -> dict:
        """
        Get comprehensive service statistics.

        Returns:
            Dictionary with statistics from all components
        """
        return {
            'service': {
                'running': self.running,
                'total_polls': self.poll_count,
            },
            'tracker': self.tracker.get_statistics(),
            'state': self.state_manager.get_statistics(),
            'storage': self.file_store.get_statistics(),
            'metadata': self.metadata_store.get_statistics(),
            'rate_limiter': self.rate_limiter.get_statistics()
        }
