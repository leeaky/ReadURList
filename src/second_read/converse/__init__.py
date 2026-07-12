from __future__ import annotations

import json
import logging
import math
from typing import Optional

from second_read.config import Settings
from second_read.db import Claim, Item, Message, get_session
from second_read.llm.base import LLMProvider
from second_read.prompts import CONVERSE_SYSTEM

logger = logging.getLogger(__name__)


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _load_embedding(raw: Optional[str]) -> Optional[list[float]]:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def retrieve_context(question: str, llm: LLMProvider, settings: Settings, top_k: int = 8) -> str:
    q_emb = llm.embed([question], model=settings.model_embed)[0]
    session = get_session()
    try:
        claims = session.query(Claim).all()
        scored: list[tuple[float, Claim]] = []
        for c in claims:
            emb = _load_embedding(c.embedding_json)
            if not emb:
                continue
            scored.append((_cosine(q_emb, emb), c))
        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:top_k]
        if not top or top[0][0] < 0.35:
            return ""

        blocks: list[str] = []
        for sim, claim in top:
            item: Item = claim.item
            blocks.append(
                f"- [{item.title}]({item.url}) (sim={sim:.2f})\n"
                f"  Claim: {claim.text}\n"
                f"  Summary: {item.summary_one_liner}"
            )
        return "\n".join(blocks)
    finally:
        session.close()


def answer_from_corpus(
    question: str,
    llm: LLMProvider,
    settings: Settings,
    *,
    telegram_message_id: int | None = None,
) -> str:
    session = get_session()
    try:
        session.add(
            Message(telegram_message_id=telegram_message_id, role="user", text=question)
        )
        session.commit()
    finally:
        session.close()

    context = retrieve_context(question, llm, settings)
    if not context:
        reply = (
            "I don't have enough in your saved corpus to answer that yet. "
            "Save more URLs, or ask about something you've already captured."
        )
    else:
        prompt = (
            f"User question:\n{question}\n\n"
            f"Corpus excerpts (use only these):\n{context}"
        )
        reply = llm.complete(
            prompt,
            model=settings.model_converse,
            system=CONVERSE_SYSTEM,
            temperature=0.3,
        ).strip()

    session = get_session()
    try:
        session.add(Message(role="assistant", text=reply))
        session.commit()
    finally:
        session.close()

    return reply
