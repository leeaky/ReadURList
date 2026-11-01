from __future__ import annotations

from readurlist.config import Settings
from readurlist.db import Item, get_session
from readurlist.effort import word_count
from readurlist.ingest.arxiv import abs_url, arxiv_id, paper_word_count, pdf_word_count
from readurlist.ingest.extract import ExtractError, FetchError, extract_article
from readurlist.ingest.summarize import summarize_article
from readurlist.ingest.untrusted import assess
from readurlist.llm.base import LLMProvider
from readurlist.tags.vocab import load_vocabulary

INGEST_READY = "ready"
INGEST_PENDING_BODY = "pending_body"
# Tripwire (R-0003 layer 4): text that looks like it instructs the AI waits on
# Unfetched until the owner releases (read without the scan) or deletes it.
INGEST_HELD = "held"
INGEST_RELEASED = "released"
NOT_AVAILABLE = "not available"


def held_note(signals: list[str]) -> str:
    return f"held: looks like it instructs the AI ({', '.join(signals)})"


def _save_stub(
    *,
    url: str,
    title: str,
    note: str,
    note_clean: str | None,
    status: str = INGEST_PENDING_BODY,
    text: str = "",
) -> tuple[Item, bool]:
    session = get_session()
    try:
        existing = session.query(Item).filter_by(url=url).one_or_none()
        if existing:
            session.expunge(existing)
            return existing, False
        item = Item(
            url=url,
            title=title or url,
            snapshot=NOT_AVAILABLE,
            subject=NOT_AVAILABLE,
            topics=[],
            keywords=[],
            extracted_text=text,
            priority=3,
            note=note if status == INGEST_HELD else (note_clean or note),
            ingest_status=status,
        )
        session.add(item)
        session.commit()
        session.refresh(item)
        session.expunge(item)
        return item, True
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _paper_words(url: str, paper_id: str | None, pdf_url: str | None) -> int | None:
    """Words in the full paper (stages 11 and 12), or None to keep the page's count."""
    if paper_id:
        return paper_word_count(paper_id)
    if pdf_url:
        return pdf_word_count(pdf_url, page_url=url)
    return None


def ingest_url(
    url: str,
    llm: LLMProvider,
    settings: Settings,
    note: str | None = None,
) -> tuple[Item, bool]:
    """Fetch, snapshot, persist. Returns (item, created). Dedup skips re-fetch."""
    note_clean = note.strip() if note and note.strip() else None

    session = get_session()
    try:
        existing = session.query(Item).filter_by(url=url).one_or_none()
        if existing:
            if note_clean is not None:
                existing.note = note_clean
                session.commit()
                session.refresh(existing)
            session.expunge(existing)
            return existing, False
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    paper_id = arxiv_id(url)
    try:
        # An arXiv link of any form is read from its abstract page.
        title_hint, text, pdf_url = extract_article(abs_url(paper_id) if paper_id else url)
    except FetchError as exc:
        return _save_stub(url=url, title=url, note=str(exc), note_clean=note_clean)
    except ExtractError as exc:
        return _save_stub(url=url, title=exc.title, note=str(exc), note_clean=note_clean)

    scan = assess(f"{title_hint}\n{text}")
    if scan.suspicious:
        return _save_stub(
            url=url,
            title=title_hint or url,
            note=held_note(scan.signals),
            note_clean=note_clean,
            status=INGEST_HELD,
            text=text,
        )

    vocab = load_vocabulary()
    result = summarize_article(
        llm,
        model=settings.model_ingest,
        url=url,
        title_hint=title_hint,
        text=text,
        existing_subjects=vocab.subjects,
        existing_topics=vocab.topics,
    )

    session = get_session()
    try:
        existing = session.query(Item).filter_by(url=url).one_or_none()
        if existing:
            if note_clean is not None:
                existing.note = note_clean
                session.commit()
                session.refresh(existing)
            session.expunge(existing)
            return existing, False

        item = Item(
            url=url,
            title=result.title,
            snapshot=result.snapshot,
            subject=result.subject,
            topics=list(result.topics),
            keywords=list(result.keywords),
            extracted_text=text,
            word_count=_paper_words(url, paper_id, pdf_url) or word_count(text),
            priority=result.priority,
            note=note_clean,
            ingest_status=INGEST_READY,
        )
        session.add(item)
        session.commit()
        session.refresh(item)
        session.expunge(item)
        return item, True
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
