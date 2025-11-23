#!/usr/bin/env python3
"""
Basic example: Search PubMed for articles on microbial ecology.

Usage:
    python basic_search.py
"""

import logging
from ncbi_client.client import NCBIClient

# Enable logging to see rate limiting in action
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def main():
    # Initialize client (replace with your email)
    with NCBIClient(email="your.email@example.com") as client:
        print("Searching PubMed for 'microbial ecology' articles...\n")

        # Perform search
        results = client.esearch(
            db="pubmed",
            term="microbial ecology[Title]",
            retmax=10,
            sort="pub_date"
        )

        # Display results
        print(f"Total articles found: {results['count']:,}")
        print(f"Returned {len(results['idlist'])} IDs:\n")

        for i, pmid in enumerate(results['idlist'], 1):
            print(f"  {i}. PMID: {pmid}")

        print(f"\nQuery translation: {results.get('querytranslation', 'N/A')}")


if __name__ == "__main__":
    main()