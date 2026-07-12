from __future__ import annotations

INGEST_SYSTEM = """You extract durable knowledge from articles for a personal corpus.
Return JSON only. Keep the one-line summary factual and short — no teaser, no hype.
Claims must be atomic, checkable assertions stated in the article's voice (paraphrase OK).
Prefer 3–8 strong claims over many weak ones. Skip fluff, ads, and navigation."""

INGEST_SCHEMA = {
    "name": "ingest_result",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "title": {"type": "string"},
            "summary_one_liner": {"type": "string"},
            "claims": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": ["title", "summary_one_liner", "claims"],
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
