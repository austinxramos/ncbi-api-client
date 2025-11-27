import os
from typing import Optional

import click

from .client import NCBIClient
from .cache import CacheManager
from .config import DEFAULT_CACHE_DIR


def _build_client(
    email: Optional[str],
    api_key: Optional[str],
    use_cache: bool,
) -> NCBIClient:
    """Construct an NCBIClient with optional on-disk caching."""
    # Allow email from env var if not passed explicitly
    if not email:
        email = os.getenv("NCBI_EMAIL")

    if not email:
        raise click.UsageError(
            "Email must be provided via --email or NCBI_EMAIL environment variable."
        )

    cache = None
    if use_cache:
        cache = CacheManager(cache_dir=DEFAULT_CACHE_DIR)  # <-- NO db_name here

    return NCBIClient(email=email, api_key=api_key, cache=cache)


@click.group()
@click.option(
    "--email",
    envvar="NCBI_EMAIL",
    help="Email address required by NCBI (or set NCBI_EMAIL).",
)
@click.option(
    "--api-key",
    envvar="NCBI_API_KEY",
    help="Optional NCBI API key (or set NCBI_API_KEY).",
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Disable on-disk caching.",
)
@click.pass_context
def main(ctx: click.Context, email: str, api_key: Optional[str], no_cache: bool) -> None:
    """NCBI E-utilities command line client."""
    client = _build_client(email=email, api_key=api_key, use_cache=not no_cache)
    ctx.obj = {"client": client}


@main.command()
@click.argument("term")
@click.option(
    "--db",
    default="pubmed",
    show_default=True,
    help="NCBI database to search.",
)
@click.option(
    "--max-results",
    "retmax",
    type=int,
    default=20,
    show_default=True,
    help="Maximum number of IDs to return.",
)
@click.pass_context
def search(ctx: click.Context, term: str, db: str, retmax: int) -> None:
    """Run an ESearch query and print the matching IDs."""
    client: NCBIClient = ctx.obj["client"]
    results = client.esearch(db=db, term=term, retmax=retmax)

    click.echo(f"Total results: {results['count']}")
    ids = results.get("idlist", [])
    click.echo(f"Returned {len(ids)} IDs:")
    for id_ in ids:
        click.echo(f"  {id_}")


if __name__ == "__main__":
    main()
