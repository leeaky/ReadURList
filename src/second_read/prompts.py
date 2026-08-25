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

CONNECT_SYSTEM = """You compare claims from a personal reading corpus.
Label ONLY genuine claim-level relationships. Same topic is NOT enough.
Types (strongest first): contradicts, answers, extends, related.
If there is no real relationship, set type to "none".
Rationale must cite both claims concretely. Never invent tension."""

CONNECT_SCHEMA = {
    "name": "relationship_label",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "type": {
                "type": "string",
                "enum": ["contradicts", "answers", "extends", "related", "none"],
            },
            "strength": {"type": "number"},
            "rationale": {"type": "string"},
        },
        "required": ["type", "strength", "rationale"],
    },
}

PING_SYSTEM = """You compose a corpus ping for a personal knowledge bot.
Rules:
- Hook: one line stating the genuine tension or connection — never clickbait.
- Analysis: short, accurate; after reading it the hook must feel fair.
- Question: one question that invites a reply (tension, contradiction, open thread).
Never recap a single article. The value is what you did with the corpus."""

PING_SCHEMA = {
    "name": "ping_message",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "hook": {"type": "string"},
            "analysis": {"type": "string"},
            "question": {"type": "string"},
        },
        "required": ["hook", "analysis", "question"],
    },
}

CONVERSE_SYSTEM = """You answer ONLY from the user's saved corpus excerpts provided.
Cite sources with their URLs in markdown links.
If the corpus cannot answer, say so plainly. Never present outside knowledge as if it came from the corpus."""
