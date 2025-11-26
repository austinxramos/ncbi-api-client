"""Tests for NCBI client."""
import pytest
from ncbi_client.client import NCBIClient
#from ncbi_client.exceptions import APIError


def test_client_initialization():
    """Test client can be initialized."""
    client = NCBIClient(email="test@example.com")
    assert client.email == "test@example.com"
    assert client.api_key is None
    client.close()


def test_client_context_manager():
    """Test client works as context manager."""
    with NCBIClient(email="test@example.com") as client:
        assert client.email == "test@example.com"


def test_esearch_pubmed():
    """Test basic PubMed search."""
    with NCBIClient(email="test@example.com") as client:
        results = client.esearch(
            db="pubmed",
            term="microbial ecology",
            retmax=5
        )

        assert "count" in results
        assert "idlist" in results
        assert isinstance(results["count"], int)
        assert isinstance(results["idlist"], list)
        assert len(results["idlist"]) <= 5


def test_esearch_with_filters():
    """Test search with additional filters."""
    with NCBIClient(email="test@example.com") as client:
        results = client.esearch(
            db="pubmed",
            term="microbial ecology[Title] AND 2023[PDAT]",
            retmax=10
        )

        assert results["count"] >= 0
        assert len(results["idlist"]) <= 10


@pytest.mark.parametrize("db", ["pubmed", "nucleotide", "protein"])
def test_esearch_different_databases(db):
    """Test search across different NCBI databases."""
    with NCBIClient(email="test@example.com") as client:
        results = client.esearch(
            db=db,
            term="test",
            retmax=1
        )

        assert "count" in results
        assert "idlist" in results


def test_efetch_single_record():
    """Test fetching a single PubMed record."""
    with NCBIClient(email="test@example.com") as client:
        # Use a known stable PMID
        xml_data = client.efetch(
            db="pubmed",
            ids=["11748933"],  # Famous "Initial sequencing of human genome" paper
            rettype="abstract",
            retmode="xml"
        )

        assert xml_data is not None
        assert len(xml_data) > 0
        assert "PubmedArticle" in xml_data


def test_efetch_with_cache():
    """Test that efetch uses cache."""
    import tempfile
    from pathlib import Path
    from ncbi_client.cache import CacheManager

    with tempfile.TemporaryDirectory() as tmpdir:
        cache = CacheManager(cache_dir=Path(tmpdir))

        with NCBIClient(email="test@example.com", cache=cache) as client:
            ids = ["11748933"]

            # First call - should hit API
            data1 = client.efetch(db="pubmed", ids=ids, retmode="xml")

            # Second call - should use cache
            data2 = client.efetch(db="pubmed", ids=ids, retmode="xml")

            assert data1 == data2

            stats = cache.get_stats()
            assert stats["total_hits"] >= 1


def test_batch_fetch_with_progress():
    """Test batch fetching with progress callback."""
    progress_calls = []

    def track_progress(current, total):
        progress_calls.append((current, total))

    with NCBIClient(email="test@example.com") as client:
        # Search for some IDs
        results = client.esearch(db="pubmed", term="test", retmax=10)

        if results["idlist"]:
            batches = client.efetch_batch(
                db="pubmed",
                ids=results["idlist"][:10],
                batch_size=5,
                progress_callback=track_progress
            )

            assert len(batches) == 2  # 10 IDs / 5 per batch
            assert len(progress_calls) == 2
            assert progress_calls[-1] == (2, 2)  # Final call