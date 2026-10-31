from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass

from readurlist.ingest.untrusted import wrap_untrusted
from readurlist.llm.base import LLMProvider
from readurlist.prompts import INGEST_SCHEMA, INGEST_SYSTEM
from readurlist.tags.normalize import canonicalize_label, unique_labels

MAX_SNAPSHOT = 1200
MAX_SUBJECT = 80
MAX_LABEL = 60


class AnswerRejected(ValueError):
    """The model's answer did not fit the fixed form (R-0003 layer 2)."""


def _check_answer(data: object) -> dict:
    if not isinstance(data, dict):
        raise AnswerRejected("answer is not an object")
    for key in ("title", "snapshot", "subject"):
        if not isinstance(data.get(key), str):
            raise AnswerRejected(f"{key} is not text")
    snapshot = data["snapshot"].strip()
    if not snapshot or len(snapshot) > MAX_SNAPSHOT:
        raise AnswerRejected(f"snapshot length {len(snapshot)} outside 1–{MAX_SNAPSHOT}")
    subject = data["subject"].strip()
    if not subject or len(subject) > MAX_SUBJECT:
        raise AnswerRejected(f"subject length {len(subject)} outside 1–{MAX_SUBJECT}")
    for key in ("topics", "keywords"):
        values = data.get(key)
        if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
            raise AnswerRejected(f"{key} is not a list of text")
        if any(len(v.strip()) > MAX_LABEL for v in values):
            raise AnswerRejected(f"a {key[:-1]} is longer than {MAX_LABEL} characters")
    priority = data.get("priority")
    if type(priority) is not int or not 1 <= priority <= 5:
        raise AnswerRejected(f"priority {priority!r} is not 1–5")
    return data


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
    prompt = vocab_block + wrap_untrusted(
        f"Extracted title hint: {title_hint}\n\nArticle text:\n{clipped}", url
    )
    raw = llm.complete(
        prompt,
        model=model,
        system=INGEST_SYSTEM,
        schema=INGEST_SCHEMA,
        temperature=0.2,
    )
    try:
        data = _check_answer(json.loads(raw))
    except json.JSONDecodeError as exc:
        raise AnswerRejected("answer is not JSON") from exc
    priority_int = data["priority"]
    snapshot = data["snapshot"].strip()
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
