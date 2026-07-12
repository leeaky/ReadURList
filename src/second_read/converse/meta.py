from __future__ import annotations

import re

from second_read.db import Item, Relationship, get_session

_LIST_RE = re.compile(
    r"\b("
    r"list|what have i saved|what did i save|show (me )?(my )?(saves|articles|urls|links|corpus)|"
    r"how many|saved (urls|articles|items)|my (saves|articles|corpus)"
    r")\b",
    re.IGNORECASE,
)
_OVERVIEW_RE = re.compile(
    r"\b("
    r"summarise|summarize|overview|recap (everything|all)|"
    r"sum up (everything|all|my corpus)|what's in (my )?(corpus|saves)"
    r")\b",
    re.IGNORECASE,
)
_RELATED_RE = re.compile(
    r"\b("
    r"related|connected|connection|contradict|contradiction|"
    r"how (do|are) (they|these|the) .+ related|any (links|connections)"
    r")\b",
    re.IGNORECASE,
)


def detect_meta_intent(question: str) -> str | None:
    q = question.strip()
    if not q:
        return None
    # Order matters: related before list (list is broader)
    if _RELATED_RE.search(q):
        return "related"
    if _OVERVIEW_RE.search(q):
        return "overview"
    if _LIST_RE.search(q):
        return "list"
    return None


def handle_meta_intent(intent: str) -> str:
    if intent == "list":
        return _list_saves()
    if intent == "overview":
        return _overview()
    if intent == "related":
        return _related()
    return "I didn't understand that corpus request."


def _list_saves() -> str:
    session = get_session()
    try:
        items = session.query(Item).order_by(Item.created_at.desc()).all()
        if not items:
            return "Your corpus is empty. Paste a URL to save something."
        lines = [f"You have {len(items)} saved item(s):\n"]
        for i, item in enumerate(items, 1):
            lines.append(f"{i}. {item.title}\n   {item.summary_one_liner}\n   {item.url}")
        return "\n".join(lines)
    finally:
        session.close()


def _overview() -> str:
    session = get_session()
    try:
        items = session.query(Item).order_by(Item.created_at.asc()).all()
        if not items:
            return "Nothing to summarise yet — your corpus is empty."
        lines = [f"Corpus overview ({len(items)} items):\n"]
        for item in items:
            lines.append(f"• {item.title} — {item.summary_one_liner}\n  {item.url}")
        return "\n".join(lines)
    finally:
        session.close()


def _related() -> str:
    session = get_session()
    try:
        rels = (
            session.query(Relationship)
            .order_by(Relationship.strength.desc())
            .limit(20)
            .all()
        )
        item_count = session.query(Item).count()
        if item_count < 2:
            return "Need at least two saved items before I can find relationships."
        if not rels:
            return (
                "I haven't found any claim-level relationships yet. "
                "That can be correct with a small corpus — save more, or the items may not truly connect."
            )
        lines = [f"Found {len(rels)} relationship(s) (strongest first):\n"]
        for rel in rels:
            a = rel.claim_a.item
            b = rel.claim_b.item
            lines.append(
                f"• {rel.type} ({rel.strength:.2f})\n"
                f"  {a.title} ↔ {b.title}\n"
                f"  {a.url}\n  {b.url}\n"
                f"  {rel.rationale}"
            )
        return "\n".join(lines)
    finally:
        session.close()
