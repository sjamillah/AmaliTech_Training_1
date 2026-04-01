from __future__ import annotations
"""CLI entry point for LAB_5 async scraping workflow."""

import argparse
import asyncio
import logging

from .extractor import filter_successful, map_to_summary, process_results
from .fetcher import fetch_all
from .storage import save_results

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

DEMO_URLS = [
    "https://www.python.org/",  # Tech / programming
    "https://www.wikipedia.org/",  # Education / general reference
    "https://www.bbc.com/news",  # News / media
    "https://www.nationalgeographic.com/",  # Science / culture / nature
    "https://www.imdb.com/chart/top/",  # Entertainment / lists
    "https://www.khanacademy.org/",  # Education / tutorials
    "https://www.nytimes.com/section/world",  # News / global events
    "https://www.nationalgeographic.com/animals",  # Nature / animals
    "https://www.cookingchanneltv.com/",  # Lifestyle / food
    "https://www.goodreads.com/quotes",  # Literature / quotes
]


async def scrape(urls: list[str]) -> None:
    """Fetch, enrich, summarise, and persist scraped results for the given URLs."""
    print(f"\nFetching {len(urls)} URLs concurrently...")
    raw = await fetch_all(urls)

    enriched = []
    async for result in process_results(raw):
        enriched.append(result)

    successful = filter_successful(enriched)
    summaries = map_to_summary(successful)

    print(f"  Fetched   : {len(raw)}")
    print(f"  Succeeded : {len(successful)}")
    for s in summaries:
        print(f"  [{s['status']}] {s['url']}")
        print(f"         title={s['title']!r}  words={s['words']}  links={s['links']}")

    path = await save_results(summaries)
    print(f"\nSaved to: {path}")


def main() -> None:
    """Parse CLI arguments and run benchmark or scraping flow."""
    parser = argparse.ArgumentParser()
    parser.add_argument("urls", nargs="*", help="URLs to scrape")
    parser.add_argument("--demo", action="store_true", help="Run against demo URLs")
    parser.add_argument(
        "--bench", action="store_true", help="Run performance benchmark"
    )
    args = parser.parse_args()

    urls = DEMO_URLS if args.demo or not args.urls else args.urls

    if args.bench:
        from .performance import benchmark

        benchmark(urls[:4])
    else:
        asyncio.run(scrape(urls))


if __name__ == "__main__":
    main()
