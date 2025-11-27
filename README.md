# NCBI E-utilities API Client

A robust Python client for the NCBI E-utilities API with automatic rate limiting, retry logic, local caching, and a simple command-line interface.

## Features

- ✅ **Rate limiting** – Automatic compliance with NCBI usage guidelines (3 req/sec without API key, higher with key)
- ✅ **Retry logic** – Exponential backoff for transient failures
- ✅ **SQLite caching** – Persistent cache with deduplicated entries and hit counters
- ✅ **Type safety** – Pydantic models for request/response validation
- ✅ **Batch processing** – Automatic chunking for large ID lists with progress tracking
- ✅ **Comprehensive logging** – Track requests, cache hits, and rate limiting
- ✅ **Multiple databases** – Works with PubMed, Nucleotide, Protein, and other NCBI databases
- ✅ **CLI tool** – `ncbi-fetch` command for quick terminal workflows

---

## Installation

From a clone of this repo, inside your virtualenv:

```bash
pip install -e .
````

For development (tests, formatting, type checking):

```bash
pip install -e ".[dev]"
```

This also installs the `ncbi-fetch` console script into your virtualenv.

---

## Quick Start (Python)

### Basic Search

```python
from ncbi_client.client import NCBIClient

with NCBIClient(email="your.email@example.com") as client:
    results = client.esearch(
        db="pubmed",
        term="microbial ecology[Title]",
        retmax=100,
    )

    print(f"Found {results['count']} articles")
    print("First 10 IDs:", results["idlist"][:10])
```

### With Caching

```python
from ncbi_client.client import NCBIClient
from ncbi_client.cache import CacheManager

cache = CacheManager(max_age_days=7)

with NCBIClient(email="your.email@example.com", cache=cache) as client:
    # First call hits the API
    results1 = client.esearch(
        db="pubmed",
        term="ocean microbiome",
        retmax=200,
    )

    # Second call uses cache (much faster)
    results2 = client.esearch(
        db="pubmed",
        term="ocean microbiome",
        retmax=200,
    )

    print(cache.get_stats())
```

### Batch Fetching

```python
from ncbi_client.client import NCBIClient

def show_progress(current, total):
    print(f"Progress: {current}/{total} batches")

with NCBIClient(email="your.email@example.com") as client:
    # Get IDs from search
    results = client.esearch(
        db="pubmed",
        term="CRISPR",
        retmax=500,
    )

    ids = results["idlist"]

    # Batch fetch full records
    batches = client.efetch_batch(
        db="pubmed",
        ids=ids,
        batch_size=100,
        rettype="abstract",
        retmode="xml",
        progress_callback=show_progress,
    )

    print(f"Retrieved {len(batches)} batches")
```

---

## Command-line Usage

After installation, the `ncbi-fetch` command is available in your environment:

```bash
ncbi-fetch --help
```

You’ll see:

```text
Usage: ncbi-fetch [OPTIONS] COMMAND [ARGS]...

  NCBI E-utilities command line client.

Options:
  --email TEXT    Email address required by NCBI (or set NCBI_EMAIL).
  --api-key TEXT  Optional NCBI API key (or set NCBI_API_KEY).
  --no-cache      Disable on-disk caching.
  --help          Show this message and exit.

Commands:
  search  Run an ESearch query and print the matching IDs.
```

### Examples

Search PubMed for “test” and return up to 5 IDs:

```bash
ncbi-fetch search "test" --max-results 5
```

Specify a different NCBI database:

```bash
ncbi-fetch search "kinase" --db protein --max-results 10
```

Use environment variables for configuration:

```bash
export NCBI_EMAIL="your.email@example.com"
export NCBI_API_KEY="your_api_key"  # optional

ncbi-fetch search "microbial ecology" --db pubmed --max-results 10
```

Disable on-disk caching:

```bash
ncbi-fetch --no-cache search "CRISPR" --db pubmed --max-results 20
```

The CLI uses the same underlying `NCBIClient` as the Python API: rate limiting, retries, and optional caching are handled automatically.

---

## API Coverage

* [x] **ESearch** – Search NCBI databases and return IDs
* [x] **EFetch** – Fetch full records by ID
* [x] **Batch operations** – `efetch_batch()` for large ID lists
* [ ] **ESummary** – Planned
* [ ] **ELink** – Planned

---

## Examples

See the `examples/` directory:

* `basic_search.py` – Simple PubMed search
* `batch_fetch.py` – Batch retrieval with caching and progress reporting
* `cache_demo.py` – Demonstrates cache speedup and stats

---

## Architecture

```text
ncbi_client/
├── client.py       # Main API client with rate limiting + caching hooks
├── cache.py        # SQLite caching layer (CacheManager)
├── models.py       # Pydantic validation models (ESearchResult, etc.)
├── config.py       # Configuration constants (URLs, timeouts, rate limits)
├── exceptions.py   # Custom exception hierarchy
└── cli.py          # Click-based CLI (ncbi-fetch)
```

---

## Caching Details

The cache uses SQLite to store API responses with:

* **Hash-based keys** – Deterministic keys from endpoint + params
* **Hit counting** – Track how often entries are reused
* **Automatic expiration** – Configurable `max_age_days`
* **Integrity checks** – Cached payloads are validated before use

Default cache location:

```text
~/.ncbi_cache/ncbi_cache.db
```

Managing the cache:

```python
from ncbi_client.cache import CacheManager

cache = CacheManager()

# View stats
print(cache.get_stats())

# Clear old entries
cache.clear_stale()

# Clear all cached entries
cache.clear_all()
```

---

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

---

## Performance

With caching enabled (rough ballpark numbers):

* **First query**: ~0.5–1.0s (network + NCBI)
* **Cached query**: ~0.001–0.005s (disk + Python)
* **Batch fetch (hundreds of IDs)**: network-bound the first time, then essentially instant from cache

Actual performance depends on your network and NCBI’s current load.

---

## NCBI Usage Guidelines

This client is designed to respect NCBI’s usage policies:

* Conservative rate limiting by default
* Higher throughput when API key is provided
* Descriptive `User-Agent` header
* Email included with each request (required by NCBI)

For heavy workloads, request an API key from NCBI and pass it to the client or set `NCBI_API_KEY`.

---

## License

MIT License

---

## Author

**Xavier Ramos** (`xarnyc@protonmail.com`)

Built to demonstrate API client design, caching strategies, and scientific data workflow automation.


