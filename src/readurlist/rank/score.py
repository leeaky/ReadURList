from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Sequence

from readurlist.effort import effort

# Build map stage 5: two parts out of 100 (owner, 2026-10-31: "A").
SUBJECT_POINTS = 65
RECENCY_POINTS = 35

# Stage 6: 3 short + 1 long (owner, 2026-10-31: "A"); at most two per subject.
SHORT_PICKS = 3
LONG_PICKS = 1
PER_SUBJECT = 2


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
    word_count: int | None = None


@dataclass
class Pick:
    item_id: int
    score: int
    reason: str
    rank: int = 0
    subject_points: int = 0
    recency_points: int = 0
    section: str = "short"


@dataclass
class DayList:
    picks: list[Pick]
    # Every unread item's score, picked or not (for "points after" on fallen-off links).
    scores: dict[int, Pick] = field(default_factory=dict)
    # Unread items that scored into their section but lost out to the per-subject cap.
    capped: set[int] = field(default_factory=set)


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


def _section(item: RankItem) -> str:
    # Unknown length (no word count) counts as short.
    if item.word_count is None:
        return "short"
    return effort(item.word_count)[0]


def build_day_list(items: Sequence[RankItem], *, now: datetime) -> DayList:
    unread = [i for i in items if i.read_at is None and i.skipped_at is None]
    counts = _subject_counts(unread)
    biggest = max(counts.values(), default=1)

    scores: dict[int, Pick] = {}
    for item in unread:
        same = counts[_norm(item.subject)]
        age = _age_days(item, now)
        subject = round(SUBJECT_POINTS * same / biggest)
        recency = round(RECENCY_POINTS / (1.0 + age))
        scores[item.id] = Pick(
            item_id=item.id,
            score=subject + recency,
            reason=_reason(item, same_subject=same, age_days=age, subject=subject, recency=recency),
            subject_points=subject,
            recency_points=recency,
            section=_section(item),
        )

    by_id = {i.id: i for i in unread}
    ordered = sorted(scores.values(), key=lambda p: (-p.score, p.item_id))
    room = {"short": SHORT_PICKS, "long": LONG_PICKS}
    per_subject: dict[str, int] = {}
    picks: list[Pick] = []
    capped: set[int] = set()
    for pick in ordered:
        if room[pick.section] == 0:
            continue
        key = _norm(by_id[pick.item_id].subject) or "misc"
        if per_subject.get(key, 0) >= PER_SUBJECT:
            capped.add(pick.item_id)
            continue
        per_subject[key] = per_subject.get(key, 0) + 1
        room[pick.section] -= 1
        picks.append(pick)

    for rank, pick in enumerate(sorted(picks, key=lambda p: p.section != "short"), 1):
        pick.rank = rank
    picks.sort(key=lambda p: p.rank)
    return DayList(picks=picks, scores=scores, capped=capped)
