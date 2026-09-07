from __future__ import annotations

INGEST_SYSTEM = """You extract a reading snapshot from an article for a reading corpus.
Return JSON only. Be factual — no teaser, no hype, no clickbait.
snapshot: 2–4 sentences covering what the piece is and why it might matter.
subject: one short shared bucket (e.g. Claude Code, not a paper title). Reuse an existing subject from the prompt exactly unless none fit.
topics: 3–6 labels; reuse existing topic strings when they apply; mint only when needed.
keywords: 5–15 specific keywords or named entities (people, papers, products).
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

CONSOLIDATE_SYSTEM = """You merge near-duplicate subject and topic labels for a reading corpus.
Return JSON only — never an empty response. Merge labels that mean the same bucket (e.g. Claude Code / Claude Code training / Claude 101 course → Claude Code).
Do not collapse distinct domains into a tiny generic list (public health stays separate from LLM papers).
Do not invent new items. Identity mapping is allowed; empty arrays are valid. Do not output keywords, titles, or snapshots."""

CONSOLIDATE_SCHEMA = {
    "name": "tag_consolidation",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "subject_maps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "from": {"type": "string"},
                        "to": {"type": "string"},
                    },
                    "required": ["from", "to"],
                },
            },
            "topic_maps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "from": {"type": "string"},
                        "to": {"type": "string"},
                    },
                    "required": ["from", "to"],
                },
            },
        },
        "required": ["subject_maps", "topic_maps"],
    },
}
