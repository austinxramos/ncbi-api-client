import time
import logging
from logging import Logger
from typing import Dict, Any, Optional, List

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
from .models import ESearchResult

logger: Logger = logging.getLogger(__name__)


def _normalize_esearchresult_payload(esr: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize raw esearchresult dict so it matches our ESearchResult model.

    NCBI sometimes returns a mixed-type 'translationstack' list, e.g.:
      [{'term': ...}, 'GROUP']
    Our Pydantic model expects a list of dicts, so we drop any non-dict items.
    """
    if not isinstance(esr, dict):
        return esr

    normalized = esr.copy()
    ts = normalized.get("translationstack")

    if isinstance(ts, list):
        normalized["translationstack"] = [
            item for item in ts if isinstance(item, dict)
        ]

    return normalized


class NCBIClient:
    """
    Client for NCBI E-utilities API with rate limiting and caching.
    """

    def __init__(
        self,
        email: str,
        api_key: Optional[str] = None,
        rate_limit: Optional[float] = None,
        cache: Any = None,  # optional cache manager (e.g., CacheManager)
    ):
        """
        Initialize NCBI client.

        Args:
            email: Email address for NCBI API (required by NCBI guidelines)
            api_key: Optional NCBI API key for higher rate limits
            rate_limit: Optional custom rate limit (seconds between requests)
            cache: Optional cache manager instance (ncbi_client.cache.CacheManager)
        """
        self.email = email
        self.api_key = api_key
        self.cache = cache  # store the cache on the instance

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
            f"has_api_key={api_key is not None}, has_cache={cache is not None})"
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
        """
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

            if response.status_code == 429:
                logger.warning("Rate limit exceeded, will retry")
                raise RateLimitError("NCBI rate limit exceeded")

            response.raise_for_status()
            return response

        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise APIError(
                f"NCBI API request failed: {e}",
                status_code=getattr(e.response, "status_code", None),
            )

    def esearch(
        self,
        db: str,
        term: str,
        retmax: int = 20,
        retstart: int = 0,
        sort: Optional[str] = None,
        use_cache: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Search an NCBI database using ESearch.

        Returns a dict with keys like:
            - count: Total number of results (int)
            - retmax: Max results returned (int)
            - retstart: Starting index (int)
            - idlist: List of matching IDs
        """
        params = {
            "db": db,
            "term": term,
            "retmax": retmax,
            "retstart": retstart,
            "retmode": "json",
        }

        if sort:
            params["sort"] = sort
        params.update(kwargs)

        cache = getattr(self, "cache", None)
        cache_key = params.copy()

        # 1) Try cache first
        if use_cache and cache is not None:
            cached = cache.get("esearch", cache_key)
            if cached is not None:
                try:
                    esr_raw = cached["esearchresult"]
                    esr = _normalize_esearchresult_payload(esr_raw)

                    result_model = ESearchResult(**esr)
                    result = result_model.model_dump()

                    logger.info(
                        f"ESearch (cache): db={db}, term='{term}', "
                        f"found {result['count']} results, "
                        f"returned {len(result.get('idlist', []))} IDs"
                    )
                    return result
                except Exception as e:
                    logger.warning(f"Cache validation failed for esearch: {e}")

        # 2) No cache or invalid cache → real HTTP request
        response = self._make_request("esearch.fcgi", params)
        data = response.json()

        if "esearchresult" not in data:
            raise APIError(f"Unexpected response format: {data}")

        # Optional: store raw API data in cache
        if use_cache and cache is not None:
            cache.set("esearch", cache_key, data)

        # 3) Normalize for Pydantic model (same for cached and fresh)
        esr_raw = data["esearchresult"]
        esr = _normalize_esearchresult_payload(esr_raw)

        result_model = ESearchResult(**esr)
        result = result_model.model_dump()

        logger.info(
            f"ESearch: db={db}, term='{term}', "
            f"found {result['count']} results, "
            f"returned {len(result.get('idlist', []))} IDs"
        )

        return result

    def efetch(
        self,
        db: str,
        ids: List[str],
        rettype: str = "abstract",
        retmode: str = "xml",
        **kwargs,
    ) -> str:
        """
        Fetch full records from NCBI database using EFetch.
        """
        id_string = ",".join(str(id_) for id_ in ids)

        params = {
            "db": db,
            "id": id_string,
            "rettype": rettype,
            "retmode": retmode,
        }
        params.update(kwargs)

        cache = getattr(self, "cache", None)
        if cache is not None:
            cached = cache.get("efetch", params)
            if cached is not None:
                return cached.get("data", "")

        response = self._make_request("efetch.fcgi", params)
        data = response.text

        if cache is not None:
            cache.set("efetch", params, {"data": data})

        logger.info(
            f"EFetch: db={db}, fetched {len(ids)} records, size={len(data)} bytes"
        )

        return data

    def efetch_batch(
        self,
        db: str,
        ids: List[str],
        batch_size: int = 100,
        rettype: str = "abstract",
        retmode: str = "xml",
        progress_callback: Optional[callable] = None,
        **kwargs,
    ) -> List[str]:
        """
        Fetch records in batches with progress tracking.
        """
        if batch_size > 500:
            logger.warning(
                f"Batch size {batch_size} exceeds recommended max of 500"
            )

        results: List[str] = []
        num_batches = (len(ids) + batch_size - 1) // batch_size

        logger.info(
            f"Starting batch fetch: {len(ids)} IDs in {num_batches} batches"
        )

        for i in range(0, len(ids), batch_size):
            batch = ids[i : i + batch_size]
            batch_num = i // batch_size + 1

            logger.debug(f"Fetching batch {batch_num}/{num_batches}")

            data = self.efetch(
                db=db,
                ids=batch,
                rettype=rettype,
                retmode=retmode,
                **kwargs,
            )
            results.append(data)

            if progress_callback:
                progress_callback(batch_num, num_batches)

        logger.info(f"Completed batch fetch: {num_batches} batches")
        return results

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
