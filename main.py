#!/usr/bin/env python3
"""
Kaggle Data Ingestion Engine
Main entry point for the continuous polling service.

This service monitors Kaggle for new datasets, downloads them locally,
and stores comprehensive metadata in JSON format.

Usage:
    python main.py

Environment Variables:
    KAGGLE_USERNAME - Kaggle API username
    KAGGLE_KEY - Kaggle API key

Configuration:
    See config/config.yaml for polling intervals, storage paths, etc.
"""

import sys
from pathlib import Path

from config.settings import Settings
from src.utils.logger import setup_logger
from src.services.ingestion_service import IngestionService


def main():
    """Main entry point for the Kaggle data ingestion engine."""
    print("=" * 60)
    print("Kaggle Data Ingestion Engine")
    print("=" * 60)

    # Load configuration
    try:
        settings = Settings.load()
        print(f"Configuration loaded from: config/config.yaml")
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        print("Please ensure config/config.yaml exists in the project directory.")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to load configuration: {e}", file=sys.stderr)
        sys.exit(1)

    # Setup logger
    try:
        logger = setup_logger(settings.logging)
        logger.info("=" * 60)
        logger.info("Kaggle Data Ingestion Engine Starting")
        logger.info("=" * 60)
    except Exception as e:
        print(f"ERROR: Failed to setup logger: {e}", file=sys.stderr)
        sys.exit(1)

    # Validate configuration
    try:
        settings.validate()
        logger.info("Configuration validated successfully")
    except ValueError as e:
        logger.critical(f"Configuration validation failed: {e}")
        print(f"\nERROR: {e}", file=sys.stderr)
        print("\nPlease set your Kaggle API credentials:")
        print("1. Go to https://www.kaggle.com/settings/account")
        print("2. Click 'Create New API Token'")
        print("3. Download kaggle.json")
        print("4. Set environment variables in .env file:")
        print("   KAGGLE_USERNAME=your_username")
        print("   KAGGLE_KEY=your_api_key")
        sys.exit(1)

    # Create necessary directories
    try:
        settings.storage.datasets_dir.mkdir(parents=True, exist_ok=True)
        settings.storage.metadata_dir.mkdir(parents=True, exist_ok=True)
        settings.storage.state_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Storage directories verified")
    except Exception as e:
        logger.critical(f"Failed to create storage directories: {e}")
        sys.exit(1)

    # Print configuration summary
    logger.info("Configuration:")
    logger.info(f"  Polling interval: {settings.polling.interval_seconds} seconds")
    logger.info(f"  Max datasets per poll: {settings.kaggle.max_datasets_per_poll}")
    logger.info(f"  Datasets directory: {settings.storage.datasets_dir}")
    logger.info(f"  Metadata directory: {settings.storage.metadata_dir}")
    logger.info(f"  State directory: {settings.storage.state_dir}")
    logger.info(f"  Log file: {settings.logging.file}")

    # Initialize and start ingestion service
    try:
        logger.info("Initializing ingestion service...")
        service = IngestionService(settings)

        logger.info("Starting ingestion service...")
        print(f"\nService started! Logs: {settings.logging.file}")
        print("Press Ctrl+C to stop.\n")

        service.start()

    except KeyboardInterrupt:
        logger.info("Service interrupted by user")
        print("\nService stopped by user.")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        print(f"\nFATAL ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
