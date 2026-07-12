from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

import httpx
import trafilatura

logger = logging.getLogger(__name__)

URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)


def find_urls(text: str) -> list[str]:
    return URL_RE.findall(text or "")


def extract_article(url: str, timeout: float = 30.0) -> tuple[str, str]:
    """Fetch URL and extract main text. Returns (title, text). Raises on failure."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme}")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; SecondRead/0.1; +https://github.com/local/second-read)"
        )
    }
    with httpx.Client(follow_redirects=True, timeout=timeout, headers=headers) as client:
        response = client.get(url)
        response.raise_for_status()
        html = response.text

    extracted = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=False,
        favor_precision=True,
        url=url,
        output_format="txt",
    )
    meta = trafilatura.extract_metadata(html) if html else None
    title = (meta.title if meta and meta.title else "") or url

    if not extracted or len(extracted.strip()) < 80:
        raise ValueError("Could not extract enough article text from URL")

    return title.strip(), extracted.strip()
