from __future__ import annotations

import json
import logging

from second_read.config import Settings
from second_read.db import Item, get_session
from second_read.llm.base import LLMProvider
from second_read.prompts import CONSOLIDATE_SCHEMA, CONSOLIDATE_SYSTEM
from second_read.tags.normalize import should_consolidate
from second_read.tags.vocab import apply_tag_maps, load_vocabulary

logger = logging.getLogger(__name__)

BATCH = 80


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
        for start in range(0, ready_count, BATCH):
            chunk = ready[start : start + BATCH]
            lines = [
                f"id={row.id} | title={row.title} | subject={row.subject} | topics={', '.join(row.topics or [])}"
                for row in chunk
            ]
            prompt = (
                "Existing subjects so far:\n"
                + "\n".join(f"- {s}" for s in known_subjects)
                + "\nExisting topics so far:\n"
                + "\n".join(f"- {t}" for t in known_topics)
                + "\n\nItems:\n"
                + "\n".join(lines)
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
