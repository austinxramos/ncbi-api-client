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