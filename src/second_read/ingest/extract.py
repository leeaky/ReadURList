from __future__ import annotations

import logging
import random
import re
import time
from urllib.parse import urlparse

import httpx
import trafilatura

logger = logging.getLogger(__name__)

URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)

# Browser-like headers — bot-identifying UAs get throttled more often.
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
}

_RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}
_MAX_ATTEMPTS = 4
_BASE_BACKOFF_SEC = 1.5


class FetchError(Exception):
    """Raised when a page cannot be fetched after retries."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def find_urls(text: str) -> list[str]:
    return URL_RE.findall(text or "")


def _retry_after_seconds(response: httpx.Response, attempt: int) -> float:
    header = response.headers.get("Retry-After")
    if header:
        try:
            return max(float(header), 0.5)
        except ValueError:
            pass
    # Exponential backoff with jitter
    return _BASE_BACKOFF_SEC * (2 ** (attempt - 1)) + random.uniform(0, 0.75)


def _fetch_html(url: str, timeout: float) -> str:
    last_exc: Exception | None = None
    with httpx.Client(
        follow_redirects=True,
        timeout=timeout,
        headers=_BROWSER_HEADERS,
    ) as client:
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                response = client.get(url)
                if response.status_code in _RETRYABLE_STATUS:
                    wait = _retry_after_seconds(response, attempt)
                    logger.warning(
                        "Fetch %s → HTTP %s (attempt %s/%s); retry in %.1fs",
                        url,
                        response.status_code,
                        attempt,
                        _MAX_ATTEMPTS,
                        wait,
                    )
                    if attempt == _MAX_ATTEMPTS:
                        raise FetchError(
                            f"Site rate-limited or unavailable (HTTP {response.status_code}). "
                            "Try again in a minute.",
                            status_code=response.status_code,
                        )
                    time.sleep(wait)
                    continue
                response.raise_for_status()
                return response.text
            except httpx.TimeoutException as exc:
                last_exc = exc
                wait = _BASE_BACKOFF_SEC * attempt
                logger.warning(
                    "Fetch timeout for %s (attempt %s/%s); retry in %.1fs",
                    url,
                    attempt,
                    _MAX_ATTEMPTS,
                    wait,
                )
                if attempt == _MAX_ATTEMPTS:
                    break
                time.sleep(wait)
            except httpx.TransportError as exc:
                last_exc = exc
                wait = _BASE_BACKOFF_SEC * attempt
                logger.warning(
                    "Fetch transport error for %s: %s (attempt %s/%s)",
                    url,
                    exc,
                    attempt,
                    _MAX_ATTEMPTS,
                )
                if attempt == _MAX_ATTEMPTS:
                    break
                time.sleep(wait)
            except httpx.HTTPStatusError as exc:
                code = exc.response.status_code
                raise FetchError(
                    f"Could not fetch page (HTTP {code}).",
                    status_code=code,
                ) from exc

    raise FetchError(f"Could not fetch page after {_MAX_ATTEMPTS} attempts: {last_exc}")


def extract_article(url: str, timeout: float = 30.0) -> tuple[str, str]:
    """Fetch URL and extract main text. Returns (title, text). Raises on failure."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme}")

    html = _fetch_html(url, timeout=timeout)

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
