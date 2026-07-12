from __future__ import annotations

import logging
from datetime import datetime, timedelta

from second_read.db import Item, Ping, Relationship, get_session

logger = logging.getLogger(__name__)

TYPE_RANK = {
    "contradicts": 4,
    "answers": 3,
    "extends": 2,
    "related": 1,
}


def select_relationship(
    *,
    min_strength: float = 0.5,
) -> Relationship | None:
    """Pick the best unsurfaced relationship, or None if nothing qualifies."""
    session = get_session()
    try:
        rels = (
            session.query(Relationship)
            .filter(Relationship.surfaced_at.is_(None))
            .filter(Relationship.strength >= min_strength)
            .all()
        )
        if not rels:
            return None

        scored: list[tuple[float, Relationship]] = []
        for rel in rels:
            claim_a = rel.claim_a
            claim_b = rel.claim_b
            item_a: Item = claim_a.item
            item_b: Item = claim_b.item

            type_score = TYPE_RANK.get(rel.type, 0)
            # Prefer never-surfaced items
            surface_penalty = item_a.surfaced_count + item_b.surfaced_count
            # Prefer time span (days between items)
            delta = abs((item_a.created_at - item_b.created_at).total_seconds()) / 86400.0
            time_bonus = min(delta / 30.0, 2.0)

            score = (
                type_score * 10
                + rel.strength * 5
                + time_bonus
                - surface_penalty * 2
            )
            # Drop weak "related" unless strong
            if rel.type == "related" and rel.strength < 0.8:
                continue
            scored.append((score, rel))

        if not scored:
            return None
        scored.sort(key=lambda x: x[0], reverse=True)
        best = scored[0][1]
        # Detach for use outside session
        session.expunge(best)
        return best
    finally:
        session.close()


def pings_sent_today() -> int:
    session = get_session()
    try:
        start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return session.query(Ping).filter(Ping.sent_at >= start).count()
    finally:
        session.close()


def within_quiet_hours(start_hour: int, end_hour: int, now: datetime | None = None) -> bool:
    now = now or datetime.now()
    hour = now.hour
    if start_hour <= end_hour:
        return start_hour <= hour < end_hour
    # overnight window
    return hour >= start_hour or hour < end_hour


def recently_checked(meta_key: str, interval_minutes: int) -> bool:
    """Return True if we should skip because we checked too recently."""
    from second_read.db import Meta

    session = get_session()
    try:
        row = session.get(Meta, meta_key)
        if not row:
            return False
        try:
            last = datetime.fromisoformat(row.value)
        except ValueError:
            return False
        return datetime.now() - last < timedelta(minutes=interval_minutes)
    finally:
        session.close()


def mark_checked(meta_key: str) -> None:
    from second_read.db import Meta

    session = get_session()
    try:
        row = session.get(Meta, meta_key)
        if row:
            row.value = datetime.now().isoformat()
        else:
            session.add(Meta(key=meta_key, value=datetime.now().isoformat()))
        session.commit()
    finally:
        session.close()
