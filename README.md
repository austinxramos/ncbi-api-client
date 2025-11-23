# NCBI E-utilities API Client

A robust Python client for the NCBI E-utilities API with automatic rate limiting, retry logic, and local caching.

## Features

- ✅ **Rate limiting** - Automatic compliance with NCBI usage guidelines (3 req/sec without API key, 10 req/sec with key)
- ✅ **Retry logic** - Exponential backoff for transient failures
- ✅ **Type safety** - Pydantic models for request/response validation
- ✅ **Local caching** - SQLite-based cache to avoid redundant API calls
- ✅ **Comprehensive logging** - Track all requests and rate limit enforcement
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
```python
from ncbi_client.client import NCBIClient

# Initialize client
with NCBIClient(email="your.email@example.com") as client:
    
    # Search PubMed
    results = client.esearch(
        db="pubmed",
        term="microbial ecology[Title]",
        retmax=100
    )
    
    print(f"Found {results['count']} articles")
    print(f"First 10 PMIDs: {results['idlist'][:10]}")
```

## API Coverage (Day 1 - In Progress)

- [x] **ESearch** - Search NCBI databases
- [ ] **EFetch** - Retrieve full records (Day 2)
- [ ] **ESummary** - Retrieve document summaries (Day 2)
- [ ] **ELink** - Find related records (Day 3)

## Usage Examples

See `examples/` directory:
- `basic_search.py` - Simple PubMed search
- `batch_fetch.py` - Batch retrieval with caching (coming Day 2)

## Architecture
```
ncbi_client/
├── client.py       # Main API client with rate limiting
├── cache.py        # SQLite caching layer (Day 2)
├── models.py       # Pydantic validation models (Day 2)
├── config.py       # Configuration constants
└── exceptions.py   # Custom exceptions
```

## Development

Run tests:
```bash
pytest tests/ -v
```

Format code:
```bash
black ncbi_client/ tests/
```

Type checking:
```bash
mypy ncbi_client/
```

## NCBI Usage Guidelines

This client automatically enforces NCBI's usage policies:
- Maximum 3 requests/second without API key
- Maximum 10 requests/second with API key
- Descriptive User-Agent header
- Email address in all requests

For large-scale data retrieval, consider requesting an API key from NCBI.

## License

MIT License - see LICENSE file

## Author

Xavier Ramos (xarnyc@protonmail.com)
Built as a demonstration of API client design, error handling, and scientific data workflow automation.