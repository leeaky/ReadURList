from __future__ import annotations

import json
from dataclasses import dataclass

from second_read.llm.base import LLMProvider
from second_read.prompts import INGEST_SCHEMA, INGEST_SYSTEM


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
) -> IngestResult:
    clipped = text[:max_chars]
    prompt = (
        f"URL: {url}\n"
        f"Extracted title hint: {title_hint}\n\n"
        f"Article text:\n{clipped}"
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
    one_liner = (data.get("summary_one_liner") or "").strip()
    return IngestResult(
        title=(data.get("title") or title_hint).strip() or title_hint,
        snapshot=snapshot or one_liner,
        subject=(data.get("subject") or "").strip(),
        topics=_clip_list(data.get("topics"), cap=8),
        keywords=_clip_list(data.get("keywords"), cap=15),
        priority=priority_int,
    )


# Old name kept so leftover call sites fail loudly if re-enabled.
summarize_and_claim = summarize_article
