"""
Rate limiter to prevent API throttling.
Implements simple time-based rate limiting (KISS principle).
Follows Single Responsibility Principle: Only handles rate limiting.
"""

import time
import logging
from typing import Optional

from src.utils.logger import get_logger


class RateLimiter:
    """
    Simple time-based rate limiter for API requests.
    Ensures minimum interval between consecutive requests.
    """

    def __init__(self, min_interval_seconds: float = 1.0):
        """
        Initialize rate limiter.

        Args:
            min_interval_seconds: Minimum time interval between requests in seconds
        """
        self.min_interval = min_interval_seconds
        self.last_request_time: Optional[float] = None
        self.logger = get_logger(__name__)
        self.total_requests = 0
        self.total_wait_time = 0.0

    def wait_if_needed(self) -> None:
        """
        Wait if necessary to maintain minimum interval between requests.
        Call this before making an API request.
        """
        if self.last_request_time is None:
            # First request, no wait needed
            self.last_request_time = time.time()
            self.total_requests += 1
            return

        # Calculate time since last request
        time_since_last = time.time() - self.last_request_time

        # Wait if needed
        if time_since_last < self.min_interval:
            wait_time = self.min_interval - time_since_last
            self.logger.debug(f"Rate limiting: waiting {wait_time:.2f} seconds")
            time.sleep(wait_time)
            self.total_wait_time += wait_time

        self.last_request_time = time.time()
        self.total_requests += 1

    def record_request(self) -> None:
        """
        Record that a request was made.
        Use this if you want to track requests without automatic waiting.
        """
        self.last_request_time = time.time()
        self.total_requests += 1

    def handle_rate_limit_error(self, retry_after: int = 60) -> None:
        """
        Handle rate limit error from API by waiting.

        Args:
            retry_after: Number of seconds to wait (default: 60)
        """
        self.logger.warning(
            f"Rate limit hit! Waiting {retry_after} seconds before retrying..."
        )
        time.sleep(retry_after)
        self.last_request_time = time.time()

    def reset(self) -> None:
        """Reset the rate limiter state."""
        self.last_request_time = None
        self.total_requests = 0
        self.total_wait_time = 0.0
        self.logger.debug("Rate limiter reset")

    def get_statistics(self) -> dict:
        """
        Get statistics about rate limiting.

        Returns:
            Dictionary with rate limiting statistics
        """
        return {
            'total_requests': self.total_requests,
            'total_wait_time_seconds': round(self.total_wait_time, 2),
            'min_interval_seconds': self.min_interval,
            'last_request_time': self.last_request_time
        }
