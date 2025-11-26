#!/usr/bin/env python3
"""
Example: Batch fetch PubMed articles with caching and progress tracking.

This demonstrates:
- Searching for a large set of articles
- Batch fetching with automatic chunking
- Progress feedback during long operations
- Cache utilization to avoid redundant requests

Usage:
    python batch_fetch.py
"""

import logging
from ncbi_client.client import NCBIClient
from ncbi_client.cache import CacheManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


def progress_callback(current, total):
    """Display progress bar."""
    pct = (current / total) * 100
    bar_length = 40
    filled = int(bar_length * current / total)
    bar = "=" * filled + "-" * (bar_length - filled)
    print(f"\r[{bar}] {current}/{total} batches ({pct:.1f}%)", end="", flush=True)


def main():
    # Initialize cache
    cache = CacheManager(max_age_days=7)  # Cache results for 1 week

    print("Initializing NCBI client with caching enabled...\n")

    with NCBIClient(
            email="your.email@example.com",
            cache=cache
    ) as client:

        # First search - will hit API
        print("Searching for 'ocean microbiome' articles...")
        results = client.esearch(
            db="pubmed",
            term="ocean microbiome[Title/Abstract]",
            retmax=250,  # Get 250 IDs
            sort="pub_date"
        )

        print(f"Found {results['count']:,} total articles")
        print(f"Retrieved {len(results['idlist'])} IDs for fetching\n")

        if not results['idlist']:
            print("No results to fetch.")
            return

        # Batch fetch abstracts
        print("Fetching article abstracts in batches...")
        print("(This will be cached for future runs)\n")

        batches = client.efetch_batch(
            db="pubmed",
            ids=results['idlist'],
            batch_size=50,  # 50 articles per batch
            rettype="abstract",
            retmode="xml",
            progress_callback=progress_callback
        )

        print("\n\nFetch complete!")
        print(f"Retrieved {len(batches)} batches")

        # Show total size
        total_size = sum(len(batch) for batch in batches)
        print(f"Total data: {total_size:,} bytes ({total_size / 1024:.1f} KB)")

        # Display cache stats
        print("\n" + "=" * 50)
        print("Cache Statistics:")
        print("=" * 50)
        stats = cache.get_stats()
        print(f"Total cached entries: {stats['total_entries']}")
        print(f"Total cache hits: {stats['total_hits']}")
        print("\nBy endpoint:")
        for endpoint, data in stats['by_endpoint'].items():
            print(f"  {endpoint}: {data['count']} entries")

        print("\n" + "=" * 50)
        print("Try running this script again - it will use cached results!")
        print("=" * 50)


if __name__ == "__main__":
    main()