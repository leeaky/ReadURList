"""arXiv papers get their reading length from the full paper (build map stage 11).

The abstract page gives the title and the text the summary is written from, as for
any page. The PDF is downloaded only to count its words; its text is never stored or
shown to the model (owner, 2026-11-01: "Abstract, length from paper").
"""
from __future__ import annotations

import io
import logging
import re
import time

import httpx
from pypdf import PdfReader

from readurlist.effort import word_count

logger = logging.getLogger(__name__)
# pypdf reports every odd font or figure it meets; the count doesn't need them.
logging.getLogger("pypdf").setLevel(logging.CRITICAL)

# New ids (2410.12345, optional version) and old ones (hep-th/9901001).
_ARXIV = re.compile(
    r"^https?://(?:www\.|export\.)?arxiv\.org/(?:abs|pdf|html)/"
    r"((?:\d{4}\.\d{4,5}|[a-z\-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?)(?:\.pdf)?/?$"
)
_MAX_PDF_BYTES = 40 * 1024 * 1024
_TIMEOUT = 60.0
_TRANSPORT: httpx.BaseTransport | None = None  # tests swap in a fake


def arxiv_id(url: str) -> str | None:
    match = _ARXIV.match(url.strip())
    return match.group(1) if match else None


def abs_url(paper_id: str) -> str:
    return f"https://arxiv.org/abs/{paper_id}"


def paper_word_count(paper_id: str) -> int | None:
    """Words in the paper's PDF, or None if it can't be fetched or read."""
    url = f"https://arxiv.org/pdf/{paper_id}"

    def skip(reason: str) -> None:
        logger.warning("arXiv %s (%s): %s; kept the abstract count", paper_id, abs_url(paper_id), reason)

    try:
        with httpx.Client(follow_redirects=True, timeout=_TIMEOUT, transport=_TRANSPORT) as client:
            with client.stream("GET", url) as response:
                if response.status_code == 404:
                    skip("PDF not found (HTTP 404)")
                    return None
                response.raise_for_status()
                body = bytearray()
                for chunk in response.iter_bytes():
                    body += chunk
                    if len(body) > _MAX_PDF_BYTES:
                        skip(f"PDF over {_MAX_PDF_BYTES // (1024 * 1024)} MB")
                        return None
        reader = PdfReader(io.BytesIO(bytes(body)))
        words = sum(word_count(page.extract_text() or "") for page in reader.pages)
    except httpx.HTTPError as exc:
        skip(f"PDF could not be downloaded ({exc.__class__.__name__})")
        return None
    except Exception as exc:
        skip(f"PDF could not be read ({exc.__class__.__name__})")
        return None
    if not words:
        skip("no text in the PDF")
        return None
    return words


def fix_saved_papers(*, sleep=time.sleep) -> tuple[int, int]:
    """One-off: count saved arXiv papers from their PDF. Returns (fixed, failed)."""
    from readurlist.db import Item, get_session

    session = get_session()
    try:
        rows = [
            (row, paper_id)
            for row in session.query(Item).filter(Item.ingest_status == "ready").order_by(Item.id)
            if (paper_id := arxiv_id(row.url))
        ]
        fixed = failed = 0
        for n, (row, paper_id) in enumerate(rows):
            if n:
                sleep(3.0)  # arXiv asks automated readers to pause between requests
            words = paper_word_count(paper_id)
            if words is None:
                failed += 1
                continue
            row.word_count = words
            session.commit()
            fixed += 1
        return fixed, failed
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def main() -> None:
    """CLI: `readurlist-arxiv-lengths` — fix the length of arXiv papers saved before stage 11."""
    from readurlist.config import get_settings
    from readurlist.db import init_db

    init_db(get_settings().database_url)
    fixed, failed = fix_saved_papers()
    print(f"arXiv papers counted from their PDF: {fixed}; kept the abstract count: {failed}")
