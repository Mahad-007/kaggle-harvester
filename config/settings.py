"""
Configuration management module.
Loads and validates configuration from YAML and environment variables.
Follows Single Responsibility Principle: Only handles configuration loading.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv


@dataclass
class KaggleConfig:
    """Kaggle API configuration."""
    username: str
    key: str
    max_datasets_per_poll: int
    sort_by: str


@dataclass
class PollingConfig:
    """Polling service configuration."""
    interval_seconds: int
    retry_attempts: int
    retry_backoff_factor: int
    initial_retry_delay: int


@dataclass
class StorageConfig:
    """Storage paths configuration."""
    datasets_dir: Path
    metadata_dir: Path
    state_dir: Path


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str
    file: Path
    max_bytes: int
    backup_count: int
    console_level: str


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    min_request_interval_seconds: float
    max_concurrent_downloads: int


@dataclass
class Settings:
    """Main settings container. Dependency Inversion: provides abstraction for configuration."""
    kaggle: KaggleConfig
    polling: PollingConfig
    storage: StorageConfig
    logging: LoggingConfig
    rate_limit: RateLimitConfig

    @classmethod
    def load(cls, config_path: str = "config/config.yaml") -> "Settings":
        """
        Load configuration from YAML and environment variables.

        Args:
            config_path: Path to YAML configuration file

        Returns:
            Settings instance with loaded configuration

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If required environment variables are missing
        """
        # Load environment variables from .env file if it exists
        load_dotenv()

        # Load YAML configuration
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)

        # Get Kaggle credentials from environment
        kaggle_username = os.getenv("KAGGLE_USERNAME")
        kaggle_key = os.getenv("KAGGLE_KEY")

        # Build configuration objects
        return cls(
            kaggle=KaggleConfig(
                username=kaggle_username or "",
                key=kaggle_key or "",
                max_datasets_per_poll=config['kaggle']['max_datasets_per_poll'],
                sort_by=config['kaggle']['sort_by']
            ),
            polling=PollingConfig(
                interval_seconds=config['polling']['interval_seconds'],
                retry_attempts=config['polling']['retry_attempts'],
                retry_backoff_factor=config['polling']['retry_backoff_factor'],
                initial_retry_delay=config['polling']['initial_retry_delay']
            ),
            storage=StorageConfig(
                datasets_dir=Path(config['storage']['datasets_dir']),
                metadata_dir=Path(config['storage']['metadata_dir']),
                state_dir=Path(config['storage']['state_dir'])
            ),
            logging=LoggingConfig(
                level=config['logging']['level'],
                file=Path(config['logging']['file']),
                max_bytes=config['logging']['max_bytes'],
                backup_count=config['logging']['backup_count'],
                console_level=config['logging']['console_level']
            ),
            rate_limit=RateLimitConfig(
                min_request_interval_seconds=config['rate_limit']['min_request_interval_seconds'],
                max_concurrent_downloads=config['rate_limit']['max_concurrent_downloads']
            )
        )

    def validate(self) -> bool:
        """
        Validate configuration values.

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        if not self.kaggle.username or not self.kaggle.key:
            raise ValueError(
                "Kaggle API credentials not configured. "
                "Please set KAGGLE_USERNAME and KAGGLE_KEY environment variables."
            )

        if self.polling.interval_seconds < 1:
            raise ValueError("Polling interval must be at least 1 second")

        if self.polling.retry_attempts < 1:
            raise ValueError("Retry attempts must be at least 1")

        if self.rate_limit.min_request_interval_seconds < 0:
            raise ValueError("Minimum request interval cannot be negative")

        return True
