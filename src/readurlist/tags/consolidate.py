from __future__ import annotations

import json
import logging

from readurlist.config import Settings
from readurlist.db import Item, get_session
from readurlist.llm.base import LLMProvider
from readurlist.prompts import CONSOLIDATE_SCHEMA, CONSOLIDATE_SYSTEM
from readurlist.tags.normalize import should_consolidate
from readurlist.tags.vocab import apply_tag_maps, load_vocabulary

logger = logging.getLogger(__name__)

BATCH = 80


def consolidation_prompt(*, subjects: list[str], topics: list[str]) -> str:
    return (
        "Map near-duplicate labels onto shared buckets. "
        "Use the existing strings exactly in from.\n"
        "Subjects:\n"
        + "\n".join(f"- {s}" for s in subjects)
        + "\nTopics:\n"
        + "\n".join(f"- {t}" for t in topics)
    )


def maps_from_payload(data: dict) -> tuple[dict[str, str], dict[str, str]]:
    def as_map(rows: object) -> dict[str, str]:
        out: dict[str, str] = {}
        if not isinstance(rows, list):
            return out
        for row in rows:
            if not isinstance(row, dict):
                continue
            src = str(row.get("from") or "").strip()
            dst = str(row.get("to") or "").strip()
            if src and dst:
                out[src] = dst
        return out

    return as_map(data.get("subject_maps")), as_map(data.get("topic_maps"))


def maybe_consolidate_tags(llm: LLMProvider, settings: Settings) -> int:
    vocab = load_vocabulary()
    session = get_session()
    try:
        ready = (
            session.query(Item)
            .filter(Item.ingest_status == "ready")
            .order_by(Item.id)
            .all()
        )
        ready_count = len(ready)
        unique_subjects = len(vocab.subjects)
        if not should_consolidate(
            ready_count=ready_count, unique_subjects=unique_subjects
        ):
            return 0

        subject_maps: dict[str, str] = {}
        topic_maps: dict[str, str] = {}
        known_subjects = list(vocab.subjects)
        known_topics = list(vocab.topics)
        for start in range(0, max(len(known_subjects), 1), BATCH):
            subject_chunk = known_subjects[start : start + BATCH]
            prompt = consolidation_prompt(
                subjects=subject_chunk or known_subjects,
                topics=known_topics,
            )
            raw = llm.complete(
                prompt,
                model=settings.model_ingest,
                system=CONSOLIDATE_SYSTEM,
                schema=CONSOLIDATE_SCHEMA,
                temperature=0.2,
            )
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                logger.exception("consolidation response was not valid JSON")
                return 0
            sm, tm = maps_from_payload(payload)
            subject_maps.update(sm)
            topic_maps.update(tm)
            for dst in sm.values():
                if dst and dst not in known_subjects:
                    known_subjects.append(dst)
            for dst in tm.values():
                if dst and dst not in known_topics:
                    known_topics.append(dst)
    finally:
        session.close()

    if not subject_maps and not topic_maps:
        return 0
    return apply_tag_maps(subject_maps=subject_maps, topic_maps=topic_maps)
