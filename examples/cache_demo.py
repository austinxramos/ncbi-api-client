#!/usr/bin/env python3
"""
Example: Demonstrate caching behavior.

Shows how caching eliminates redundant API calls and speeds up repeated queries.
"""

import time
import logging
from ncbi_client.client import NCBIClient
from ncbi_client.cache import CacheManager

logging.basicConfig(level=logging.INFO)


def main():
    cache = CacheManager()

    with NCBIClient(email="your.email@example.com", cache=cache) as client:
        query = "microbial ecology genomics"

        print("First query (will hit API)...")
        start = time.time()
        results1 = client.esearch(db="pubmed", term=query, retmax=100)
        time1 = time.time() - start
        print(f"  Found {results1['count']} results in {time1:.3f}s\n")

        print("Second query (should use cache)...")
        start = time.time()
        results2 = client.esearch(db="pubmed", term=query, retmax=100)
        time2 = time.time() - start
        print(f"  Found {results2['count']} results in {time2:.3f}s\n")

        speedup = time1 / time2 if time2 > 0 else float('inf')
        print(f"Speedup from caching: {speedup:.1f}x faster")

        # Verify results are identical
        assert results1 == results2, "Cached results don't match!"
        print("✓ Cache integrity verified - results match exactly")


if __name__ == "__main__":
    main()