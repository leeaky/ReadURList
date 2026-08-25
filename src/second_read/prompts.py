from __future__ import annotations

INGEST_SYSTEM = """You extract a reading snapshot from an article for a personal corpus.
Return JSON only. Be factual — no teaser, no hype, no clickbait.
snapshot: 2–4 sentences covering what the piece is and why it might matter.
subject: one primary subject (short noun phrase).
topics: 3–8 topic labels.
keywords: 5–15 specific keywords or named entities.
priority: 1–5 where 5 is a primary source / dense analysis and 1 is fluff or listicle."""

INGEST_SCHEMA = {
    "name": "ingest_result",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "title": {"type": "string"},
            "snapshot": {"type": "string"},
            "subject": {"type": "string"},
            "topics": {"type": "array", "items": {"type": "string"}},
            "keywords": {"type": "array", "items": {"type": "string"}},
            "priority": {"type": "integer"},
        },
        "required": [
            "title",
            "snapshot",
            "subject",
            "topics",
            "keywords",
            "priority",
        ],
    },
}
