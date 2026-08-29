from __future__ import annotations

from dataclasses import dataclass, field

from second_read.db import Item, get_session
from second_read.tags.normalize import canonicalize_label, unique_labels


@dataclass
class Vocabulary:
    subjects: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)


def load_vocabulary() -> Vocabulary:
    session = get_session()
    try:
        rows = session.query(Item).filter(Item.ingest_status == "ready").all()
        subjects: list[str] = []
        seen_s: set[str] = set()
        topics: list[str] = []
        seen_t: set[str] = set()
        for row in rows:
            subject = (row.subject or "").strip()
            if subject:
                key = canonicalize_label(subject, []).lower()
                if key and key not in seen_s:
                    seen_s.add(key)
                    subjects.append(subject)
            for topic in row.topics or []:
                label = (topic or "").strip()
                if not label:
                    continue
                key = canonicalize_label(label, []).lower()
                if key and key not in seen_t:
                    seen_t.add(key)
                    topics.append(label)
        subjects.sort(key=str.lower)
        topics.sort(key=str.lower)
        return Vocabulary(subjects=subjects, topics=topics)
    finally:
        session.close()


def _lookup(maps: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for src, dst in maps.items():
        folded = canonicalize_label(src, []).lower()
        if folded:
            out[folded] = dst
    return out


def apply_tag_maps(*, subject_maps: dict[str, str], topic_maps: dict[str, str]) -> int:
    subj_l = _lookup(subject_maps)
    topic_l = _lookup(topic_maps)
    session = get_session()
    changed = 0
    try:
        rows = session.query(Item).filter(Item.ingest_status == "ready").all()
        for row in rows:
            before_s, before_t = row.subject, list(row.topics or [])
            key = canonicalize_label(row.subject or "", []).lower()
            if key in subj_l:
                row.subject = subj_l[key]
            new_topics: list[str] = []
            for topic in row.topics or []:
                tkey = canonicalize_label(topic, []).lower()
                new_topics.append(topic_l[tkey] if tkey in topic_l else topic)
            row.topics = new_topics
            if row.subject != before_s or list(row.topics or []) != before_t:
                changed += 1

        subjects = [r.subject or "" for r in rows]
        topics_existing: list[str] = []
        for r in rows:
            topics_existing.extend(r.topics or [])
        for row in rows:
            row.subject = canonicalize_label(row.subject or "", subjects)
            row.topics = unique_labels(
                [
                    canonicalize_label(t, topics_existing)
                    for t in (row.topics or [])
                    if t
                ]
            )
        session.commit()
        return changed
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
