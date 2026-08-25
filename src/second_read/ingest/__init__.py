from __future__ import annotations

from second_read.config import Settings
from second_read.db import Item, get_session
from second_read.ingest.extract import extract_article
from second_read.ingest.summarize import summarize_article
from second_read.llm.base import LLMProvider


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

    title_hint, text = extract_article(url)
    result = summarize_article(
        llm,
        model=settings.model_ingest,
        url=url,
        title_hint=title_hint,
        text=text,
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
            priority=result.priority,
            note=note_clean,
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
