from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

# Build map stage 5: two parts out of 100 (owner, 2026-10-31: "A").
SUBJECT_POINTS = 65
RECENCY_POINTS = 35


@dataclass
class RankItem:
    id: int
    subject: str
    topics: list[str]
    keywords: list[str]
    created_at: datetime
    read_at: datetime | None
    priority: int
    skipped_at: datetime | None = None
    restored_at: datetime | None = None


@dataclass
class Pick:
    item_id: int
    score: int
    reason: str
    rank: int = 0
    subject_points: int = 0
    recency_points: int = 0


def _norm(text: str) -> str:
    return (text or "").strip().lower()


def _subject_counts(unread: Sequence[RankItem]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for u in unread:
        key = _norm(u.subject)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _aligned(when: datetime, now: datetime) -> datetime:
    if when.tzinfo is None and now.tzinfo is not None:
        return when.replace(tzinfo=now.tzinfo)
    if when.tzinfo is not None and now.tzinfo is None:
        return when.replace(tzinfo=None)
    return when


def _recency_start(item: RankItem, now: datetime) -> datetime:
    """Saved date, or the restore date when later (a restored item counts as freshly saved)."""
    start = _aligned(item.created_at, now)
    if item.restored_at is not None:
        start = max(start, _aligned(item.restored_at, now))
    return start


def _age_days(item: RankItem, now: datetime) -> float:
    return max((now - _recency_start(item, now)).total_seconds() / 86400.0, 0.0)


def _when(item: RankItem, age_days: float) -> str:
    verb = "Restored" if item.restored_at is not None and item.restored_at > item.created_at else "Saved"
    days = int(age_days)
    if days == 0:
        return f"{verb} today"
    if days == 1:
        return f"{verb} yesterday"
    return f"{verb} {days} days ago"


def _reason(item: RankItem, *, same_subject: int, age_days: float, subject: int, recency: int) -> str:
    if subject >= recency:
        lead = f"You keep saving {item.subject or 'this subject'}: {same_subject} unread"
    else:
        lead = _when(item, age_days)
    return f"{lead} (subject {subject} + recency {recency} = {subject + recency})"


def score_unread(
    items: Sequence[RankItem],
    *,
    now: datetime,
    top_n: int = 5,
) -> list[Pick]:
    unread = [i for i in items if i.read_at is None and i.skipped_at is None]
    counts = _subject_counts(unread)
    biggest = max(counts.values(), default=1)

    scored: list[tuple[int, RankItem, int, int, str]] = []
    for item in unread:
        same = counts[_norm(item.subject)]
        age = _age_days(item, now)
        subject = round(SUBJECT_POINTS * same / biggest)
        recency = round(RECENCY_POINTS / (1.0 + age))
        reason = _reason(item, same_subject=same, age_days=age, subject=subject, recency=recency)
        scored.append((subject + recency, item, subject, recency, reason))

    scored.sort(key=lambda row: (-row[0], row[1].id))

    picks: list[Pick] = []
    subject_counts: dict[str, int] = {}

    for total, item, subject, recency, reason in scored:
        key = _norm(item.subject) or "misc"
        if subject_counts.get(key, 0) >= 2:
            continue
        subject_counts[key] = subject_counts.get(key, 0) + 1
        picks.append(
            Pick(
                item_id=item.id,
                score=total,
                reason=reason,
                rank=len(picks) + 1,
                subject_points=subject,
                recency_points=recency,
            )
        )
        if len(picks) >= top_n:
            break
    return picks
