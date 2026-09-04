from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

PATH_WINDOW = 10

W_DEMAND = 0.45
W_RECENCY = 0.20
W_NOVELTY = 0.20
W_PRIORITY = 0.15


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


@dataclass
class Pick:
    item_id: int
    score: float
    reason: str
    rank: int = 0


def _norm(text: str) -> str:
    return (text or "").strip().lower()


def _topic_demand(item: RankItem, unread: Sequence[RankItem]) -> float:
    if not unread:
        return 0.0
    subject = _norm(item.subject)
    share = sum(1 for u in unread if _norm(u.subject) == subject)
    return share / len(unread)


def _recency(item: RankItem, now: datetime) -> float:
    created = item.created_at
    if created.tzinfo is None and now.tzinfo is not None:
        created = created.replace(tzinfo=now.tzinfo)
    elif created.tzinfo is not None and now.tzinfo is None:
        now = now.replace(tzinfo=created.tzinfo)
    age_days = max((now - created).total_seconds() / 86400.0, 0.0)
    return 1.0 / (1.0 + age_days)


def _path_novelty(item: RankItem, recent_read: Sequence[RankItem]) -> float:
    if not recent_read:
        return 1.0
    seen_subjects = {_norm(r.subject) for r in recent_read}
    seen_topics = set()
    for r in recent_read:
        seen_topics.update(_norm(t) for t in r.topics if t)
    if _norm(item.subject) not in seen_subjects:
        return 1.0
    item_topics = {_norm(t) for t in item.topics if t}
    if item_topics and item_topics.isdisjoint(seen_topics):
        return 0.7
    return 0.0


def _priority_norm(item: RankItem) -> float:
    p = item.priority if item.priority is not None else 3
    p = min(max(int(p), 1), 5)
    return p / 5.0


def _reason(item: RankItem, *, demand: float, novelty: float) -> str:
    bits: list[str] = []
    if demand >= 0.2:
        bits.append(f"you keep saving {item.subject or 'this topic'}")
    if novelty >= 1.0:
        bits.append("not yet on your reading path")
    if item.priority >= 4:
        bits.append("high-signal source")
    if not bits:
        bits.append("recent unread save")
    return "; ".join(bits)


def score_unread(
    items: Sequence[RankItem],
    *,
    now: datetime,
    top_n: int = 5,
) -> list[Pick]:
    unread = [i for i in items if i.read_at is None and i.skipped_at is None]
    read = [i for i in items if i.read_at is not None]
    recent_read = sorted(
        read,
        key=lambda r: r.read_at or r.created_at,
        reverse=True,
    )[:PATH_WINDOW]

    scored: list[tuple[float, RankItem, str]] = []
    for item in unread:
        demand = _topic_demand(item, unread)
        recency = _recency(item, now)
        novelty = _path_novelty(item, recent_read)
        prio = _priority_norm(item)
        total = (
            W_DEMAND * demand
            + W_RECENCY * recency
            + W_NOVELTY * novelty
            + W_PRIORITY * prio
        )
        reason = _reason(item, demand=demand, novelty=novelty)
        scored.append((total, item, reason))

    scored.sort(key=lambda row: (-row[0], row[1].id))

    picks: list[Pick] = []
    subject_counts: dict[str, int] = {}

    for total, item, reason in scored:
        subject = _norm(item.subject) or "misc"
        if subject_counts.get(subject, 0) >= 2:
            continue
        subject_counts[subject] = subject_counts.get(subject, 0) + 1
        picks.append(
            Pick(
                item_id=item.id,
                score=round(total, 4),
                reason=reason,
                rank=len(picks) + 1,
            )
        )
        if len(picks) >= top_n:
            break
    return picks
