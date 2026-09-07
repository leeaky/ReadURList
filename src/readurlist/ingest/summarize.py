from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass

from readurlist.llm.base import LLMProvider
from readurlist.prompts import INGEST_SCHEMA, INGEST_SYSTEM
from readurlist.tags.normalize import canonicalize_label, unique_labels


@dataclass
class IngestResult:
    title: str
    snapshot: str
    subject: str
    topics: list[str]
    keywords: list[str]
    priority: int


def _clip_list(values: object, *, cap: int) -> list[str]:
    if not isinstance(values, list):
        return []
    out: list[str] = []
    for raw in values:
        if isinstance(raw, str) and raw.strip():
            out.append(raw.strip())
        if len(out) >= cap:
            break
    return out


def summarize_article(
    llm: LLMProvider,
    *,
    model: str,
    url: str,
    title_hint: str,
    text: str,
    max_chars: int = 12000,
    existing_subjects: Sequence[str] | None = None,
    existing_topics: Sequence[str] | None = None,
) -> IngestResult:
    clipped = text[:max_chars]
    subjects = [s for s in (existing_subjects or []) if s]
    topics_v = [t for t in (existing_topics or []) if t]
    vocab_block = ""
    if subjects or topics_v:
        vocab_block = (
            "Existing subjects (reuse exactly unless none fit):\n"
            + "\n".join(f"- {s}" for s in subjects)
            + "\nExisting topics (reuse when they apply):\n"
            + "\n".join(f"- {t}" for t in topics_v)
            + "\n\n"
        )
    prompt = (
        vocab_block
        + f"URL: {url}\n"
        + f"Extracted title hint: {title_hint}\n\n"
        + f"Article text:\n{clipped}"
    )
    raw = llm.complete(
        prompt,
        model=model,
        system=INGEST_SYSTEM,
        schema=INGEST_SCHEMA,
        temperature=0.2,
    )
    data = json.loads(raw)
    priority = data.get("priority", 3)
    try:
        priority_int = int(priority)
    except (TypeError, ValueError):
        priority_int = 3
    priority_int = min(max(priority_int, 1), 5)
    snapshot = (data.get("snapshot") or "").strip()
    subject = canonicalize_label(data.get("subject") or "", subjects)
    topics = unique_labels(
        [
            canonicalize_label(t, topics_v)
            for t in _clip_list(data.get("topics"), cap=8)
            if canonicalize_label(t, topics_v)
        ]
    )
    return IngestResult(
        title=(data.get("title") or title_hint).strip() or title_hint,
        snapshot=snapshot,
        subject=subject,
        topics=topics,
        keywords=_clip_list(data.get("keywords"), cap=15),
        priority=priority_int,
    )
