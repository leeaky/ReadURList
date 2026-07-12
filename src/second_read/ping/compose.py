from __future__ import annotations

import json
from dataclasses import dataclass

from second_read.config import Settings
from second_read.db import Relationship
from second_read.llm.base import LLMProvider
from second_read.prompts import PING_SCHEMA, PING_SYSTEM


@dataclass
class PingContent:
    hook: str
    analysis: str
    question: str


def compose_ping(
    llm: LLMProvider,
    settings: Settings,
    rel: Relationship,
) -> PingContent:
    claim_a = rel.claim_a
    claim_b = rel.claim_b
    item_a = claim_a.item
    item_b = claim_b.item

    prompt = (
        f"Relationship type: {rel.type} (strength {rel.strength:.2f})\n"
        f"Rationale: {rel.rationale}\n\n"
        f"Source A: [{item_a.title}]({item_a.url})\n"
        f"Claim A: {claim_a.text}\n\n"
        f"Source B: [{item_b.title}]({item_b.url})\n"
        f"Claim B: {claim_b.text}\n"
    )
    raw = llm.complete(
        prompt,
        model=settings.model_ping,
        system=PING_SYSTEM,
        schema=PING_SCHEMA,
        temperature=0.4,
    )
    data = json.loads(raw)
    return PingContent(
        hook=data["hook"].strip(),
        analysis=data["analysis"].strip(),
        question=data["question"].strip(),
    )


def format_ping_message(content: PingContent, rel: Relationship) -> str:
    item_a = rel.claim_a.item
    item_b = rel.claim_b.item
    return (
        f"*{content.hook}*\n\n"
        f"{content.analysis}\n\n"
        f"{content.question}\n\n"
        f"— [{item_a.title}]({item_a.url}) ↔ [{item_b.title}]({item_b.url})"
    )
