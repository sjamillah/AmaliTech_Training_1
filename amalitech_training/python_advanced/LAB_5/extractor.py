from __future__ import annotations

import re
from typing import Any, AsyncIterator, Dict, Iterable, List, Optional

TITLE_PATTERN = re.compile(r"<title[^>]*>\s*([^<]+?)\s*</title>", re.IGNORECASE)
LINK_PATTERN = re.compile(r'href=["\']([^"\'#][^"\']*)["\']', re.IGNORECASE)
HEADING_PATTERN = re.compile(r"<h([1-3])[^>]*>\s*([^<]+?)\s*</h\1>", re.IGNORECASE)
STRIP_TAGS = re.compile(r"<[^>]+>")
WHITESPACE = re.compile(r"\s+")
WORD_PATTERN = re.compile(r"\b[a-zA-Z]\w*\b")


# Extraction synchronously
def extract_title(html: str) -> Optional[str]:
    """Return the page <title> text, or None if absent."""
    m = TITLE_PATTERN.search(html)
    return m.group(1).strip() if m else None


def extract_links(html: str) -> List[str]:
    """Return all href values found in the page."""
    return LINK_PATTERN.findall(html)


def extract_headings(html: str) -> List[str]:
    """Return text content of h1, h2, h3 elements in document order."""
    return [text.strip() for _, text in HEADING_PATTERN.findall(html)]


def word_count(html: str) -> int:
    """Count words in visible text (HTML tags stripped first)."""
    text = STRIP_TAGS.sub(" ", html)
    return len(WORD_PATTERN.findall(text))


def extract_all(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run all extractors on one fetch-result dict.
    Handles None html gracefully — returns empty values rather than raising.
    """
    html = result.get("html") or ""
    return {
        **result,
        "title": extract_title(html),
        "links": extract_links(html),
        "headings": extract_headings(html),
        "words": word_count(html),
    }


# Async generator
async def process_results(
    results: Iterable[Dict[str, Any]],
) -> AsyncIterator[Dict[str, Any]]:
    """
    Async generator — yields one enriched result dict per input.
    Caller uses `async for result in process_results(raw): ...`
    """
    for result in results:
        yield extract_all(result)


# Functional post-processing
def filter_successful(results: List[Dict]) -> List[Dict]:
    """Keep only results where HTTP status was 200."""
    return list(filter(lambda r: r.get("status") == 200, results))


def map_to_summary(results: List[Dict]) -> List[Dict]:
    """Map full result dicts to lightweight summary dicts."""

    def summarise(r: Dict) -> Dict:
        return {
            "url": r["url"],
            "title": r.get("title"),
            "words": r.get("words", 0),
            "links": len(r.get("links", [])),
            "headings": r.get("headings", []),
            "status": r.get("status"),
        }

    return list(map(summarise, results))
