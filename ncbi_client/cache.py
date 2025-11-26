"""
SQLite-based caching layer for NCBI API responses.

Implements checksum-based deduplication and automatic cache management
to minimize redundant API calls while respecting data freshness.
"""

import sqlite3
import hashlib
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from contextlib import contextmanager

from .config import DEFAULT_CACHE_DIR, CACHE_DB_NAME
from .exceptions import CacheError

logger = logging.getLogger(__name__)


class CacheManager:
    """
    SQLite-based cache for NCBI API responses.

    Features:
    - Hash-based deduplication of requests
    - Automatic expiration of stale entries
    - Hit counting for cache analytics
    - Thread-safe operations

    Example:
        >>> cache = CacheManager()
        >>> cache.set("esearch", {"term": "test"}, {"count": 100})
        >>> result = cache.get("esearch", {"term": "test"})
        >>> print(result["count"])  # 100
    """

    def __init__(self, cache_dir: Optional[Path] = None, max_age_days: int = 30):
        """
        Initialize cache manager.

        Args:
            cache_dir: Directory for cache database (default: ~/.ncbi_cache)
            max_age_days: Maximum age for cache entries before considered stale
        """
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.cache_dir / CACHE_DB_NAME
        self.max_age_days = max_age_days

        self._init_database()
        logger.info(f"Initialized cache at {self.db_path}")

    def _init_database(self):
        """Create cache table if it doesn't exist."""
        with self._get_connection() as conn:
            conn.execute("""
                         CREATE TABLE IF NOT EXISTS cache
                         (
                             cache_key
                             TEXT
                             PRIMARY
                             KEY,
                             endpoint
                             TEXT
                             NOT
                             NULL,
                             params_hash
                             TEXT
                             NOT
                             NULL,
                             response_data
                             TEXT
                             NOT
                             NULL,
                             created_at
                             TEXT
                             NOT
                             NULL,
                             hit_count
                             INTEGER
                             DEFAULT
                             0,
                             last_accessed
                             TEXT
                         )
                         """)

            # Create indices for common queries
            conn.execute("""
                         CREATE INDEX IF NOT EXISTS idx_endpoint
                             ON cache(endpoint)
                         """)
            conn.execute("""
                         CREATE INDEX IF NOT EXISTS idx_created_at
                             ON cache(created_at)
                         """)
            conn.commit()

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            raise CacheError(f"Cache database error: {e}")
        finally:
            conn.close()

    def _make_cache_key(self, endpoint: str, params: Dict[str, Any]) -> str:
        """
        Generate deterministic cache key from endpoint and parameters.

        Uses SHA256 hash of sorted JSON to ensure identical requests
        produce identical keys regardless of parameter order.
        """
        # Sort params to ensure consistent hashing
        sorted_params = json.dumps(params, sort_keys=True)
        hash_input = f"{endpoint}:{sorted_params}"
        return hashlib.sha256(hash_input.encode()).hexdigest()

    def get(self, endpoint: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached response if available and fresh.

        Args:
            endpoint: API endpoint
            params: Request parameters

        Returns:
            Cached response dict, or None if not cached or stale
        """
        cache_key = self._make_cache_key(endpoint, params)

        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT response_data, created_at, hit_count
                FROM cache
                WHERE cache_key = ?
                """,
                (cache_key,)
            )
            row = cursor.fetchone()

            if row is None:
                logger.debug(f"Cache MISS: {endpoint}")
                return None

            # Check if entry is stale
            created_at = datetime.fromisoformat(row["created_at"])
            age = datetime.utcnow() - created_at

            if age > timedelta(days=self.max_age_days):
                logger.debug(f"Cache STALE: {endpoint} (age: {age.days} days)")
                return None

            # Update hit count and last accessed time
            conn.execute(
                """
                UPDATE cache
                SET hit_count     = hit_count + 1,
                    last_accessed = ?
                WHERE cache_key = ?
                """,
                (datetime.utcnow().isoformat(), cache_key)
            )
            conn.commit()

            logger.info(
                f"Cache HIT: {endpoint} "
                f"(age: {age.days}d, hits: {row['hit_count'] + 1})"
            )

            return json.loads(row["response_data"])

    def set(self, endpoint: str, params: Dict[str, Any], response: Dict[str, Any]):
        """
        Store response in cache.

        Args:
            endpoint: API endpoint
            params: Request parameters
            response: Response data to cache
        """
        cache_key = self._make_cache_key(endpoint, params)
        params_hash = hashlib.md5(
            json.dumps(params, sort_keys=True).encode()
        ).hexdigest()

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cache 
                (cache_key, endpoint, params_hash, response_data, created_at, hit_count)
                VALUES (?, ?, ?, ?, ?, 0)
                """,
                (
                    cache_key,
                    endpoint,
                    params_hash,
                    json.dumps(response),
                    datetime.utcnow().isoformat(),
                )
            )
            conn.commit()

        logger.debug(f"Cache SET: {endpoint}")

    def clear_stale(self) -> int:
        """
        Remove stale cache entries.

        Returns:
            Number of entries removed
        """
        cutoff = datetime.utcnow() - timedelta(days=self.max_age_days)

        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM cache WHERE created_at < ?",
                (cutoff.isoformat(),)
            )
            deleted = cursor.rowcount
            conn.commit()

        logger.info(f"Cleared {deleted} stale cache entries")
        return deleted

    def clear_all(self):
        """Remove all cache entries."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM cache")
            conn.commit()
        logger.info("Cleared all cache entries")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with total entries, total hits, and size by endpoint
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT COUNT(*)       as total_entries,
                       SUM(hit_count) as total_hits,
                       endpoint,
                       COUNT(*) as count
                FROM cache
                GROUP BY endpoint
                """
            )
            rows = cursor.fetchall()

            total_cursor = conn.execute(
                "SELECT COUNT(*), SUM(hit_count) FROM cache"
            )
            total_row = total_cursor.fetchone()

            return {
                "total_entries": total_row[0] or 0,
                "total_hits": total_row[1] or 0,
                "by_endpoint": {
                    row["endpoint"]: {
                        "count": row["count"],
                    }
                    for row in rows
                },
            }