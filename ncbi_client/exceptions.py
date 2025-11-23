"""Custom exceptions for NCBI API client."""
from typing import Optional


class NCBIClientError(Exception):
    """Base exception for NCBI client errors."""
    pass


class RateLimitError(NCBIClientError):
    """Raised when rate limit is exceeded."""
    pass


class APIError(NCBIClientError):
    """Raised when NCBI API returns an error."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        self.status_code = status_code
        super().__init__(message)


class ValidationError(NCBIClientError):
    """Raised when response validation fails."""
    pass


class CacheError(NCBIClientError):
    """Raised when cache operations fail."""
    pass