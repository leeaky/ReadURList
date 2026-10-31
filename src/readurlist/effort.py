"""Effort label (build map stage 4): length decides, not density.

Reading time is the word count at about 230 words a minute; short is under 15
minutes (owner, 2026-10-31: "B: 15 min"), long is 15 minutes or more.
"""
from __future__ import annotations

import argparse

from readurlist.db import Item, get_session

WORDS_PER_MINUTE = 230
SHORT_UNDER_MINUTES = 15


def word_count(text: str) -> int:
    return len((text or "").split())


def effort(words: int) -> tuple[str, int]:
    """(label, minutes) for a word count."""
    label = "short" if words / WORDS_PER_MINUTE < SHORT_UNDER_MINUTES else "long"
    return label, max(1, round(words / WORDS_PER_MINUTE))


def backfill_word_counts() -> int:
    """Set word_count on ready items saved before stage 4. Returns how many changed."""
    session = get_session()
    try:
        rows = (
            session.query(Item)
            .filter(Item.ingest_status == "ready", Item.word_count.is_(None))
            .all()
        )
        for row in rows:
            row.word_count = word_count(row.extracted_text)
        session.commit()
        return len(rows)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def main() -> None:
    argparse.ArgumentParser(
        description="One-off: label items saved before stage 4 with their word count."
    ).parse_args()
    from readurlist.config import get_settings
    from readurlist.db import init_db

    settings = get_settings()
    init_db(settings.database_url)
    print(f"Labelled {backfill_word_counts()} items.")
