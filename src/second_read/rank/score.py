from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Sequence

DUPLICATE_JACCARD = 0.6
CLUSTER_JACCARD = 0.3
PATH_WINDOW = 10

W_DEMAND = 0.35
W_CENTRAL = 0.25
W_RECENCY = 0.15
W_NOVELTY = 0.15
W_PRIORITY = 0.10


@dataclass
class RankItem:
    id: int
    subject: str
    topics: list[str]
    keywords: list[str]
    created_at: datetime
    read_at: datetime | None
    priority: int
    similar_to_item_id: int | None = None


@dataclass
class Pick:
    item_id: int
    score: float
    reason: str
    rank: int = 0


@dataclass
class Cluster:
    label: str
    item_ids: list[int] = field(default_factory=list)


def _norm(text: str) -> str:
    return (text or "").strip().lower()


def _tags(item: RankItem) -> set[str]:
    parts = [item.subject, *item.topics, *item.keywords]
    return {_norm(p) for p in parts if p and _norm(p)}


def jaccard(a: Sequence[str] | set[str], b: Sequence[str] | set[str]) -> float:
    sa = {_norm(x) for x in a if x and _norm(x)}
    sb = {_norm(x) for x in b if x and _norm(x)}
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def cluster_items(items: Sequence[RankItem], threshold: float = CLUSTER_JACCARD) -> list[Cluster]:
    """Connected components over keyword/topic Jaccard edges."""
    n = len(items)
    if n == 0:
        return []
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[rj] = ri

    for i in range(n):
        for j in range(i + 1, n):
            if jaccard(_tags(items[i]), _tags(items[j])) >= threshold:
                union(i, j)

    groups: dict[int, list[RankItem]] = {}
    for i, item in enumerate(items):
        groups.setdefault(find(i), []).append(item)

    clusters: list[Cluster] = []
    for group in groups.values():
        subjects = [_norm(g.subject) or "misc" for g in group]
        label = max(set(subjects), key=subjects.count)
        clusters.append(Cluster(label=label, item_ids=[g.id for g in group]))
    clusters.sort(key=lambda c: (-len(c.item_ids), c.label))
    return clusters


def _topic_demand(item: RankItem, unread: Sequence[RankItem]) -> float:
    if not unread:
        return 0.0
    subject = _norm(item.subject)
    share = sum(1 for u in unread if _norm(u.subject) == subject)
    return share / len(unread)


def _centrality(item: RankItem, unread: Sequence[RankItem]) -> float:
    others = [u for u in unread if u.id != item.id]
    if not others:
        return 0.0
    return _mean([jaccard(_tags(item), _tags(o)) for o in others])


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


def _is_near_dup(a: RankItem, b: RankItem) -> bool:
    return jaccard(_tags(a), _tags(b)) >= DUPLICATE_JACCARD


def _canonical_key(item: RankItem) -> tuple:
    """Higher priority, then older save, then lower id wins as cluster representative."""
    created = item.created_at.timestamp() if item.created_at else 0.0
    return (-(item.priority or 3), created, item.id)


def _keep_canonical_unread(unread: list[RankItem]) -> list[RankItem]:
    """Drop near-duplicates of a stronger unread canonical (keeps one per dup group)."""
    n = len(unread)
    if n <= 1:
        return list(unread)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(n):
        for j in range(i + 1, n):
            if _is_near_dup(unread[i], unread[j]):
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[rj] = ri

    groups: dict[int, list[RankItem]] = {}
    for i, item in enumerate(unread):
        groups.setdefault(find(i), []).append(item)
    return [min(group, key=_canonical_key) for group in groups.values()]


def _reason(item: RankItem, *, demand: float, novelty: float, dup_note: str | None) -> str:
    bits: list[str] = []
    if demand >= 0.4:
        bits.append(f"dense unread cluster on {item.subject or 'this topic'}")
    elif demand >= 0.2:
        bits.append(f"you keep saving {item.subject or 'this topic'}")
    if novelty >= 1.0:
        bits.append("not yet on your reading path")
    if item.priority >= 4:
        bits.append("high-signal source")
    if dup_note:
        bits.append(dup_note)
    if not bits:
        bits.append("recent unread save")
    return "; ".join(bits)


def score_unread(
    items: Sequence[RankItem],
    *,
    now: datetime,
    top_n: int = 5,
) -> list[Pick]:
    unread = [i for i in items if i.read_at is None]
    read = [i for i in items if i.read_at is not None]
    recent_read = sorted(
        read,
        key=lambda r: r.read_at or r.created_at,
        reverse=True,
    )[:PATH_WINDOW]
    unread = _keep_canonical_unread(unread)

    scored: list[tuple[float, RankItem, str]] = []
    for item in unread:
        if any(_is_near_dup(item, r) for r in read):
            continue
        demand = _topic_demand(item, unread)
        central = _centrality(item, unread)
        recency = _recency(item, now)
        novelty = _path_novelty(item, recent_read)
        prio = _priority_norm(item)
        total = (
            W_DEMAND * demand
            + W_CENTRAL * central
            + W_RECENCY * recency
            + W_NOVELTY * novelty
            + W_PRIORITY * prio
        )
        reason = _reason(item, demand=demand, novelty=novelty, dup_note=None)
        scored.append((total, item, reason))

    scored.sort(key=lambda row: (-row[0], row[1].id))

    picks: list[Pick] = []
    picked_items: list[RankItem] = []
    subject_counts: dict[str, int] = {}

    for total, item, reason in scored:
        subject = _norm(item.subject) or "misc"
        if subject_counts.get(subject, 0) >= 2:
            continue
        if any(_is_near_dup(item, p) for p in picked_items):
            continue
        picked_items.append(item)
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
