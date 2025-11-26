"""Tests for cache manager."""

import pytest
import tempfile
from pathlib import Path
from ncbi_client.cache import CacheManager


@pytest.fixture
def temp_cache():
    """Create temporary cache for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = CacheManager(cache_dir=Path(tmpdir), max_age_days=1)
        yield cache


def test_cache_initialization(temp_cache):
    """Test cache can be initialized."""
    assert temp_cache.db_path.exists()
    stats = temp_cache.get_stats()
    assert stats["total_entries"] == 0


def test_cache_set_and_get(temp_cache):
    """Test basic cache operations."""
    endpoint = "esearch"
    params = {"db": "pubmed", "term": "test"}
    response = {"count": 100, "idlist": ["123", "456"]}

    # Set cache
    temp_cache.set(endpoint, params, response)

    # Get cache
    cached = temp_cache.get(endpoint, params)
    assert cached is not None
    assert cached["count"] == 100
    assert len(cached["idlist"]) == 2


def test_cache_miss(temp_cache):
    """Test cache miss returns None."""
    result = temp_cache.get("esearch", {"db": "pubmed", "term": "nonexistent"})
    assert result is None


def test_cache_key_consistency(temp_cache):
    """Test that same params produce same cache key."""
    endpoint = "esearch"
    params1 = {"db": "pubmed", "term": "test", "retmax": 10}
    params2 = {"retmax": 10, "term": "test", "db": "pubmed"}  # Different order

    response = {"count": 50}

    temp_cache.set(endpoint, params1, response)

    # Should get same result with params in different order
    cached = temp_cache.get(endpoint, params2)
    assert cached is not None
    assert cached["count"] == 50


def test_cache_hit_counting(temp_cache):
    """Test that cache tracks hits."""
    endpoint = "esearch"
    params = {"db": "pubmed", "term": "test"}
    response = {"count": 100}

    temp_cache.set(endpoint, params, response)

    # Multiple gets should increment hit count
    for _ in range(5):
        temp_cache.get(endpoint, params)

    stats = temp_cache.get_stats()
    assert stats["total_hits"] == 5


def test_cache_clear_all(temp_cache):
    """Test clearing entire cache."""
    temp_cache.set("esearch", {"term": "test1"}, {"count": 1})
    temp_cache.set("esearch", {"term": "test2"}, {"count": 2})

    stats = temp_cache.get_stats()
    assert stats["total_entries"] == 2

    temp_cache.clear_all()

    stats = temp_cache.get_stats()
    assert stats["total_entries"] == 0


def test_cache_stats_by_endpoint(temp_cache):
    """Test cache statistics by endpoint."""
    temp_cache.set("esearch", {"term": "test1"}, {"count": 1})
    temp_cache.set("esearch", {"term": "test2"}, {"count": 2})
    temp_cache.set("efetch", {"id": "123"}, {"data": "xml"})

    stats = temp_cache.get_stats()

    assert "esearch" in stats["by_endpoint"]
    assert "efetch" in stats["by_endpoint"]
    assert stats["by_endpoint"]["esearch"]["count"] == 2
    assert stats["by_endpoint"]["efetch"]["count"] == 1