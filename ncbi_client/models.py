"""
Pydantic models for NCBI API request/response validation.

These models provide type safety and automatic validation for API interactions,
with graceful handling of missing or malformed fields common in scientific data.
"""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict


class ESearchResult(BaseModel):
    """
    Validated response from NCBI ESearch.

    Provides type-safe access to search results with automatic validation
    and graceful degradation for optional fields.
    """
    model_config = ConfigDict(extra='allow')  # Allow additional fields from API

    count: int = Field(..., description="Total number of matching records")
    retmax: int = Field(..., description="Number of IDs returned")
    retstart: int = Field(..., description="Starting index in result set")
    idlist: List[str] = Field(default_factory=list, description="List of matching IDs")
    translationset: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Query translation information"
    )
    translationstack: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Translation stack for complex queries"
    )
    querytranslation: Optional[str] = Field(
        default=None,
        description="Human-readable query translation"
    )
    warninglist: Optional[List[str]] = Field(
        default=None,
        description="Warnings about query terms"
    )
    errorlist: Optional[Dict[str, List[str]]] = Field(
        default=None,
        description="Errors in query processing"
    )

    @field_validator('count', 'retmax', 'retstart', mode='before')
    @classmethod
    def coerce_to_int(cls, v):
        """Convert string numbers to integers (NCBI sometimes returns strings)."""
        if isinstance(v, str):
            return int(v)
        return v

    @property
    def has_results(self) -> bool:
        """Check if search returned any results."""
        return self.count > 0 and len(self.idlist) > 0

    @property
    def has_more_results(self) -> bool:
        """Check if there are more results beyond what was returned."""
        return (self.retstart + self.retmax) < self.count


class PubMedArticle(BaseModel):
    """
    Simplified PubMed article metadata.

    Extracts key fields from complex PubMed XML/JSON responses
    with graceful handling of missing fields.
    """
    model_config = ConfigDict(extra='allow')

    pmid: str = Field(..., description="PubMed ID")
    title: Optional[str] = Field(default=None, description="Article title")
    abstract: Optional[str] = Field(default=None, description="Article abstract")
    authors: List[str] = Field(default_factory=list, description="Author names")
    journal: Optional[str] = Field(default=None, description="Journal name")
    pub_date: Optional[str] = Field(default=None, description="Publication date")
    doi: Optional[str] = Field(default=None, description="DOI")
    pmc_id: Optional[str] = Field(default=None, description="PubMed Central ID")

    @property
    def citation(self) -> str:
        """Generate simple citation string."""
        parts = []
        if self.authors:
            first_author = self.authors[0]
            parts.append(f"{first_author} et al." if len(self.authors) > 1 else first_author)
        if self.pub_date:
            parts.append(f"({self.pub_date})")
        if self.title:
            parts.append(self.title)
        if self.journal:
            parts.append(self.journal)
        return " ".join(parts) if parts else f"PMID: {self.pmid}"


class CacheEntry(BaseModel):
    """
    Model for cached API responses.

    Tracks metadata for cache validation and expiration.
    """
    model_config = ConfigDict(extra='allow')

    cache_key: str = Field(..., description="Hash-based cache key")
    endpoint: str = Field(..., description="API endpoint")
    params_hash: str = Field(..., description="Hash of request parameters")
    response_data: Union[Dict[str, Any], str] = Field(..., description="Cached response")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Cache creation time")
    hit_count: int = Field(default=0, description="Number of cache hits")

    @property
    def is_stale(self, max_age_days: int = 30) -> bool:
        """Check if cache entry is older than max_age_days."""
        age = datetime.utcnow() - self.created_at
        return age.days > max_age_days


class BatchRequest(BaseModel):
    """
    Model for batch fetch requests with progress tracking.
    """
    model_config = ConfigDict(extra='allow')

    ids: List[str] = Field(..., description="List of IDs to fetch")
    db: str = Field(..., description="NCBI database")
    batch_size: int = Field(default=100, description="Records per batch")

    @field_validator('batch_size')
    @classmethod
    def validate_batch_size(cls, v):
        """Ensure batch size is reasonable."""
        if v < 1 or v > 500:
            raise ValueError("Batch size must be between 1 and 500")
        return v

    @property
    def num_batches(self) -> int:
        """Calculate number of batches needed."""
        return (len(self.ids) + self.batch_size - 1) // self.batch_size