# NCBI E-utilities API Client

A robust Python client for the NCBI E-utilities API with automatic rate limiting, retry logic, and local caching.

## Features

- ✅ **Rate limiting** - Automatic compliance with NCBI usage guidelines (3 req/sec without API key, 10 req/sec with key)
- ✅ **Retry logic** - Exponential backoff for transient failures
- ✅ **SQLite caching** - Persistent cache with checksum-based deduplication
- ✅ **Type safety** - Pydantic models for request/response validation
- ✅ **Batch processing** - Automatic chunking for large ID lists with progress tracking
- ✅ **Comprehensive logging** - Track all requests, cache hits, and rate limit enforcement
- ✅ **Multiple databases** - Support for PubMed, Nucleotide, Protein, and all NCBI databases

## Installation
```bash
pip install -e .
```

For development:
```bash
pip install -e ".[dev]"
```

## Quick Start

### Basic Search
```python
from ncbi_client.client import NCBIClient

with NCBIClient(email="your.email@example.com") as client:
    results = client.esearch(
        db="pubmed",
        term="microbial ecology[Title]",
        retmax=100
    )
    
    print(f"Found {results['count']} articles")
```

### With Caching
```python
from ncbi_client.client import NCBIClient
from ncbi_client.cache import CacheManager

cache = CacheManager(max_age_days=7)

with NCBIClient(email="your.email@example.com", cache=cache) as client:
    # First call hits API
    results = client.esearch(db="pubmed", term="ocean microbiome", retmax=200)
    
    # Second call uses cache (instant!)
    results = client.esearch(db="pubmed", term="ocean microbiome", retmax=200)
    
    # View cache stats
    print(cache.get_stats())
```

### Batch Fetching
```python
def show_progress(current, total):
    print(f"Progress: {current}/{total} batches")

with NCBIClient(email="your.email@example.com") as client:
    # Get IDs from search
    results = client.esearch(db="pubmed", term="CRISPR", retmax=500)
    
    # Batch fetch full records
    batches = client.efetch_batch(
        db="pubmed",
        ids=results['idlist'],
        batch_size=100,
        retmode="xml",
        progress_callback=show_progress
    )
```

## API Coverage

- [x] **ESearch** - Search NCBI databases
- [x] **EFetch** - Retrieve full records
- [x] **Batch Operations** - Automatic chunking for large requests
- [ ] **ESummary** - Retrieve document summaries (Day 3)
- [ ] **ELink** - Find related records (Day 3)

## Examples

See `examples/` directory:
- `basic_search.py` - Simple PubMed search
- `batch_fetch.py` - Batch retrieval with caching and progress
- `cache_demo.py` - Demonstrates caching speedup

## Architecture
```
ncbi_client/
├── client.py       # Main API client with rate limiting
├── cache.py        # SQLite caching layer
├── models.py       # Pydantic validation models
├── config.py       # Configuration constants
└── exceptions.py   # Custom exceptions
```

## Caching Details

The cache uses SQLite to store API responses with:
- **Hash-based keys** - Deterministic caching regardless of parameter order
- **Hit counting** - Track cache efficiency
- **Automatic expiration** - Configurable max age (default 30 days)
- **Integrity checks** - Validates cached data before returning

Cache location: `~/.ncbi_cache/ncbi_cache.db`

To manage cache:
```python
from ncbi_client.cache import CacheManager

cache = CacheManager()

# View stats
print(cache.get_stats())

# Clear old entries
cache.clear_stale()

# Clear everything
cache.clear_all()
```

## Development

Run tests:
```bash
pytest tests/ -v --cov=ncbi_client
```

Format code:
```bash
black ncbi_client/ tests/
```

Type checking:
```bash
mypy ncbi_client/
```

## Performance

With caching enabled:
- **First query**: ~0.5-1.0s (network + API)
- **Cached query**: ~0.001-0.005s (1000x faster!)
- **Batch fetch (1000 IDs)**: ~50s without cache, ~0.1s with cache

## NCBI Usage Guidelines

This client automatically enforces NCBI's usage policies:
- Maximum 3 requests/second without API key
- Maximum 10 requests/second with API key  
- Descriptive User-Agent header
- Email address in all requests

For large-scale data retrieval, consider requesting an API key from NCBI.

## License

MIT License

## Author

Xavier Ramos (xarnyc@protonmail.com)  
Built to demonstrate API client design, caching strategies, and scientific data workflow automation.