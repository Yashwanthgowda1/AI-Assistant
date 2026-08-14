"""
search_client.py — Scrape DuckDuckGo (no API key needed) and return
a clean text summary for feeding into the AI prompt as context.
"""
from __future__ import annotations
import logging, textwrap
from typing import Optional

logger = logging.getLogger(__name__)

MAX_RESULTS = 3
MAX_BODY_CHARS = 300


def web_search(query: str, max_results: int = MAX_RESULTS) -> str:
    """
    Returns a formatted string of search results.
    Falls back gracefully if duckduckgo_search is not installed.
    """
    try:
        try:
            from ddgs import DDGS          # new package name
        except ImportError:
            from duckduckgo_search import DDGS  # fallback for old installs
    except ImportError:
        logger.warning("ddgs not installed; run: pip install ddgs")
        return ""

    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                title = r.get("title", "")
                body  = textwrap.shorten(r.get("body", ""), MAX_BODY_CHARS, placeholder="…")
                href  = r.get("href", "")
                results.append(f"• {title}\n  {body}\n  Source: {href}")

        if not results:
            return ""
        return "\n\n".join(results)

    except Exception as exc:
        logger.exception("Web search failed: %s", exc)
        return ""


def format_context(query: str) -> str:
    """Convenience wrapper — returns context block or empty string."""
    raw = web_search(query)
    if not raw:
        return ""
    return f"=== Web Search Results for: {query} ===\n{raw}\n=== End Results ==="
