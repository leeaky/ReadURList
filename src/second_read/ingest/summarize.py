from __future__ import annotations

import json
from dataclasses import dataclass

from second_read.llm.base import LLMProvider
from second_read.prompts import INGEST_SCHEMA, INGEST_SYSTEM


@dataclass
class IngestResult:
    title: str
    summary_one_liner: str
    claims: list[str]


def summarize_and_claim(
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
    claims = [c.strip() for c in data.get("claims", []) if isinstance(c, str) and c.strip()]
    return IngestResult(
        title=(data.get("title") or title_hint).strip(),
        summary_one_liner=(data.get("summary_one_liner") or "").strip(),
        claims=claims,
    )
