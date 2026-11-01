"""Is it working? (build map stage 10)

Read rate = distinct picks shown in the week that were marked read ÷ distinct picks
shown. Working if at least half (owner, 2026-10-31: "A"). The unread pile is shown
for background only, and its size a week ago is worked out from each item's saved,
read and skipped dates (owner, 2026-11-01): items skipped then restored, or deleted,
leave no history, so "then" can be slightly off.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone

from readurlist.db import DailyPick, Item, get_session


@dataclass(frozen=True)
class WeekStats:
    shown: int
    read: int
    skipped: int
    pile_then: int
    pile_now: int


def _aware(value: datetime | None) -> datetime | None:
    # SQLite hands datetimes back without a zone; they were stored as UTC.
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def week_stats(start: date, end: date) -> WeekStats:
    """Picks shown from start to end (inclusive); pile at the start of `start` and now."""
    since = datetime.combine(start, time.min).astimezone()
    session = get_session()
    try:
        shown_ids = {
            row.item_id
            for row in session.query(DailyPick.item_id)
            .filter(DailyPick.run_on >= start, DailyPick.run_on <= end)
        }
        shown = session.query(Item).filter(Item.id.in_(shown_ids)).all() if shown_ids else []
        read = sum(1 for i in shown if i.read_at is not None)
        skipped = sum(1 for i in shown if i.read_at is None and i.skipped_at is not None)

        ready = session.query(Item).filter(Item.ingest_status == "ready").all()
        pile_now = sum(1 for i in ready if i.read_at is None and i.skipped_at is None)
        pile_then = 0
        for i in ready:
            created, read_at, skipped_at = (
                _aware(i.created_at), _aware(i.read_at), _aware(i.skipped_at)
            )
            if created is None or created >= since:
                continue
            if read_at is not None and read_at < since:
                continue
            if skipped_at is not None and skipped_at < since:
                continue
            pile_then += 1
        return WeekStats(len(shown_ids), read, skipped, pile_then, pile_now)
    finally:
        session.close()


def week_line(stats: WeekStats, label: str = "Last week") -> str:
    pile = f"Unread pile {stats.pile_then} → {stats.pile_now}."
    if stats.shown == 0:
        return f"{label}: no picks shown. {pile}"
    rate = (200 * stats.read + stats.shown) // (2 * stats.shown)  # halves round up, as on Today
    verdict = "working" if stats.read * 2 >= stats.shown else "below half: tune the ranking"
    return (
        f"{label}: read {stats.read} of {stats.shown} picks ({rate}%, {verdict}). "
        f"Skipped {stats.skipped}. {pile}"
    )
