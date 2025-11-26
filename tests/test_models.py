"""Tests for Pydantic models."""

import pytest
from ncbi_client.models import ESearchResult, PubMedArticle, BatchRequest


def test_esearch_result_validation():
    """Test ESearchResult model validates correctly."""
    data = {
        "count": "100",  # String should be coerced to int
        "retmax": "20",
        "retstart": "0",
        "idlist": ["123", "456", "789"],
        "querytranslation": "test[All Fields]"
    }

    result = ESearchResult(**data)
    assert result.count == 100
    assert isinstance(result.count, int)
    assert len(result.idlist) == 3
    assert result.has_results is True


def test_esearch_result_empty():
    """Test ESearchResult with no results."""
    data = {
        "count": 0,
        "retmax": 20,
        "retstart": 0,
        "idlist": []
    }

    result = ESearchResult(**data)
    assert result.has_results is False
    assert result.has_more_results is False


def test_esearch_result_pagination():
    """Test ESearchResult pagination properties."""
    data = {
        "count": 1000,
        "retmax": 20,
        "retstart": 0,
        "idlist": ["1"] * 20
    }

    result = ESearchResult(**data)
    assert result.has_more_results is True


def test_pubmed_article_minimal():
    """Test PubMedArticle with minimal fields."""
    article = PubMedArticle(pmid="12345678")
    assert article.pmid == "12345678"
    assert article.title is None
    assert len(article.authors) == 0


def test_pubmed_article_citation():
    """Test citation generation."""
    article = PubMedArticle(
        pmid="12345678",
        title="Test Article",
        authors=["Smith J", "Doe J"],
        journal="Nature",
        pub_date="2023"
    )

    citation = article.citation
    assert "Smith J et al." in citation
    assert "2023" in citation
    assert "Test Article" in citation
    assert "Nature" in citation


def test_batch_request_validation():
    """Test BatchRequest validation."""
    request = BatchRequest(
        ids=["1", "2", "3"],
        db="pubmed",
        batch_size=100
    )

    assert request.num_batches == 1
    assert request.batch_size == 100


def test_batch_request_multiple_batches():
    """Test BatchRequest with multiple batches."""
    request = BatchRequest(
        ids=[str(i) for i in range(250)],
        db="pubmed",
        batch_size=100
    )

    assert request.num_batches == 3


def test_batch_request_invalid_size():
    """Test BatchRequest rejects invalid batch sizes."""
    with pytest.raises(ValueError):
        BatchRequest(
            ids=["1", "2"],
            db="pubmed",
            batch_size=1000  # Too large
        )