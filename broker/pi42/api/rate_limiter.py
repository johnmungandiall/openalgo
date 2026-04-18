"""Rate limiting for Pi42 API."""

import time
from collections import deque
from typing import Dict


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self):
        """Initialize rate limiter."""
        self.buckets: Dict[str, deque] = {}
        self.limits = {
            'place_order': (20, 1),      # 20 per second
            'cancel_order': (30, 60),    # 30 per minute
            'default': (60, 60)          # 60 per minute
        }

    def check_limit(self, endpoint: str) -> bool:
        """
        Check if request is within rate limit.

        Args:
            endpoint: API endpoint identifier

        Returns:
            True if allowed, False if rate limited
        """
        # Get limit for endpoint
        limit, window = self.limits.get(endpoint, self.limits['default'])

        # Initialize bucket if needed
        if endpoint not in self.buckets:
            self.buckets[endpoint] = deque()

        bucket = self.buckets[endpoint]
        now = time.time()

        # Remove old timestamps
        while bucket and bucket[0] < now - window:
            bucket.popleft()

        # Check if under limit
        if len(bucket) < limit:
            bucket.append(now)
            return True

        return False

    def wait_if_needed(self, endpoint: str) -> None:
        """
        Wait if rate limit exceeded.

        Args:
            endpoint: API endpoint identifier
        """
        while not self.check_limit(endpoint):
            time.sleep(0.1)


# Global rate limiter instance
rate_limiter = RateLimiter()
