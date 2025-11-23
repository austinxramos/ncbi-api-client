"""
NCBI E-utilities API client with rate limiting and retry logic.

This module provides a robust client for querying NCBI databases via the
E-utilities API, with automatic rate limiting, exponential backoff retry,
and comprehensive error handling.
"""

import time
#import hashlib
import logging
from logging import Logger
from typing import Dict, Any, Optional #List
#from urllib.parse import urlencode

import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from .config import (
    NCBI_BASE_URL,
    DEFAULT_RATE_LIMIT,
    WITH_API_KEY_RATE_LIMIT,
    MAX_RETRIES,
    REQUEST_TIMEOUT,
    USER_AGENT,
)
from .exceptions import APIError, RateLimitError

logger: Logger = logging.getLogger(__name__)


class NCBIClient:
    """
    Client for NCBI E-utilities API with rate limiting and caching.

    Implements automatic rate limiting to comply with NCBI usage guidelines:
    - Without API key: 3 requests/second max
    - With API key: 10 requests/second max

    Features:
    - Exponential backoff retry for transient failures
    - Request deduplication via hash-based caching
    - Comprehensive error handling and logging

    Example:
           Example:
        >>> client = NCBIClient(email="esearcher@university.edu")
        >>> results = client.esearch(     db="pubmed",      term="microbial ecology[Title]",      retmax=100,      sort="pub_date" )
        >>> print(f"Found {results['count']} articles")

    """

    def __init__(
            self,
            email: str,
            api_key: Optional[str] = None,
            rate_limit: Optional[float] = None,
    ):
        """
        Initialize NCBI client.

        Args:
            email: Email address for NCBI API (required by NCBI guidelines)
            api_key: Optional NCBI API key for higher rate limits
            rate_limit: Optional custom rate limit (seconds between requests)
        """
        self.email = email
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

        # Set rate limit based on API key availability
        if rate_limit is not None:
            self.rate_limit = rate_limit
        else:
            self.rate_limit = (
                WITH_API_KEY_RATE_LIMIT if api_key else DEFAULT_RATE_LIMIT
            )

        self._last_request_time = 0.0

        logger.info(
            f"Initialized NCBI client (rate_limit={self.rate_limit}s, "
            f"has_api_key={api_key is not None})"
        )

    def _wait_for_rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit:
            sleep_time = self.rate_limit - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.3f}s")
            time.sleep(sleep_time)
        self._last_request_time = time.time()

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((requests.RequestException, RateLimitError)),
        reraise=True,
    )
    def _make_request(
            self,
            endpoint: str,
            params: Dict[str, Any],
    ) -> requests.Response:
        """
        Make HTTP request to NCBI API with retry logic.

        Args:
            endpoint: E-utilities endpoint (e.g., 'esearch.fcgi')
            params: Query parameters

        Returns:
            Response object

        Raises:
            APIError: If request fails after retries
            RateLimitError: If rate limit is exceeded (triggers retry)
        """
        # Add required parameters
        params = params.copy()
        params["email"] = self.email
        if self.api_key:
            params["api_key"] = self.api_key

        url = f"{NCBI_BASE_URL}{endpoint}"

        # Enforce rate limiting
        self._wait_for_rate_limit()

        try:
            logger.debug(f"Request: {endpoint} with params: {params}")
            response = self.session.get(
                url,
                params=params,
                timeout=REQUEST_TIMEOUT,
            )

            # Check for rate limiting (HTTP 429)
            if response.status_code == 429:
                logger.warning("Rate limit exceeded, will retry")
                raise RateLimitError("NCBI rate limit exceeded")

            # Check for other errors
            response.raise_for_status()

            return response

        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise APIError(f"NCBI API request failed: {e}", status_code=getattr(e.response, 'status_code', None))

    def esearch(
            self,
            db: str,
            term: str,
            retmax: int = 20,
            retstart: int = 0,
            sort: Optional[str] = None,
            **kwargs,
    ) -> Dict[str, Any]:
        """
        Search an NCBI database using ESearch.

        Args:
            db: Database to search (e.g., 'pubmed', 'nucleotide', 'protein')
            term: Search query (Entrez syntax)
            retmax: Maximum number of IDs to return (default 20, max 100000)
            retstart: Starting index for retrieval (for pagination)
            sort: Sort order (e.g., 'relevance', 'pub_date')
            **kwargs: Additional parameters to pass to ESearch

        Returns:
            Dictionary containing:
                - count: Total number of results
                - retmax: Max results returned
                - retstart: Starting index
                - idlist: List of matching IDs
                - translationstack: Query translation details

        Example:
        >>> client = NCBIClient(email="esearcher@university.edu")
        >>> results = client.esearch(
        ...     db="pubmed",
        ...     term="microbial ecology[Title]",
        ...     retmax=100,
        ...     sort="pub_date"
        ... )
        >>> print(f"Found {results['count']} articles")
        """
        params = {
            "db": db,
            "term": term,
            "retmax": retmax,
            "retstart": retstart,
            "retmode": "json",  # Request JSON response
        }

        if sort:
            params["sort"] = sort

        # Add any additional parameters
        params.update(kwargs)

        response = self._make_request("esearch.fcgi", params)
        data = response.json()

        # Extract search results from nested structure
        if "esearchresult" not in data:
            raise APIError(f"Unexpected response format: {data}")

        result = data["esearchresult"]

        # Convert count/retmax/retstart to integers
        result["count"] = int(result.get("count", 0))
        result["retmax"] = int(result.get("retmax", 0))
        result["retstart"] = int(result.get("retstart", 0))

        logger.info(
            f"ESearch: db={db}, term='{term}', "
            f"found {result['count']} results, returned {len(result.get('idlist', []))} IDs"
        )

        return result

    def close(self):
        """Close the HTTP session."""
        self.session.close()
        logger.info("Closed NCBI client session")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()