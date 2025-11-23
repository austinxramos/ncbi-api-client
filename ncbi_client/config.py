"""Configuration for NCBI E-utilities API client."""

from pathlib import Path
from typing import Optional

# NCBI E-utilities base URL
NCBI_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

# Rate limiting: NCBI allows 3 requests/second without API key, 10/sec with key
# We'll be conservative and use 2/sec to avoid hitting limits
DEFAULT_RATE_LIMIT = 0.5  # seconds between requests (2 req/sec)
WITH_API_KEY_RATE_LIMIT = 0.15  # seconds between requests (~6 req/sec)

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2  # exponential backoff: 1s, 2s, 4s

# Cache configuration
DEFAULT_CACHE_DIR = Path.home() / ".ncbi_cache"
CACHE_DB_NAME = "ncbi_cache.db"

# Request timeout
REQUEST_TIMEOUT = 30  # seconds

# User agent (NCBI requests descriptive user agents)
USER_AGENT = "NCBI-Client/0.1.0 (Research; xarnyc@protonmail.com)"