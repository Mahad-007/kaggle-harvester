"""
Input validation utilities.
Provides reusable validation functions following DRY principle.
"""

import re
from pathlib import Path


def validate_dataset_ref(ref: str) -> bool:
    """
    Validate Kaggle dataset reference format (username/dataset-name).

    Args:
        ref: Dataset reference string

    Returns:
        True if valid format

    Raises:
        ValueError: If format is invalid
    """
    pattern = r'^[\w\-]+/[\w\-]+$'
    if not re.match(pattern, ref):
        raise ValueError(
            f"Invalid dataset reference format: '{ref}'. "
            "Expected format: 'username/dataset-name'"
        )
    return True


def validate_path(path: Path) -> bool:
    """
    Validate that a path is valid and accessible.

    Args:
        path: Path to validate

    Returns:
        True if valid

    Raises:
        ValueError: If path is invalid
    """
    if not isinstance(path, Path):
        path = Path(path)

    if path.exists() and not path.is_dir():
        raise ValueError(f"Path exists but is not a directory: {path}")

    return True


def validate_polling_interval(seconds: int) -> bool:
    """
    Validate polling interval value.

    Args:
        seconds: Polling interval in seconds

    Returns:
        True if valid

    Raises:
        ValueError: If interval is invalid
    """
    if seconds < 1:
        raise ValueError("Polling interval must be at least 1 second")

    if seconds > 86400:  # More than 24 hours
        raise ValueError("Polling interval cannot exceed 24 hours (86400 seconds)")

    return True


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing/replacing invalid characters.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename safe for filesystem
    """
    # Replace invalid characters with underscore
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, '_', filename)

    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip('. ')

    # Ensure not empty
    if not sanitized:
        sanitized = "unnamed"

    return sanitized
