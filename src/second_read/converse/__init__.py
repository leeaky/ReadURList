from __future__ import annotations

import json
import logging
import math
from typing import Optional

from second_read.config import Settings
from second_read.converse.meta import detect_meta_intent, handle_meta_intent
from second_read.db import Claim, Item, Message, get_session
from second_read.llm.base import LLMProvider
from second_read.prompts import CONVERSE_SYSTEM

logger = logging.getLogger(__name__)

# Soft floor; small corpora skip the floor and always return top-k.
SIM_FLOOR = 0.25
SMALL_CORPUS_CLAIMS = 50


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
    """Retrieve claim + title/summary hits. Soft similarity floor; small corpora always get top-k."""
    session = get_session()
    try:
        claims = session.query(Claim).all()
        items = session.query(Item).all()
        if not claims and not items:
            return ""

        # Texts to embed: question + each item's title/summary for title-style matching
        item_texts = [f"{it.title}. {it.summary_one_liner}" for it in items]
        to_embed = [question, *item_texts]
        vectors = llm.embed(to_embed, model=settings.model_embed)
        q_emb = vectors[0]
        item_embs = {items[i].id: vectors[i + 1] for i in range(len(items))}

        scored: list[tuple[float, str]] = []

        for c in claims:
            emb = _load_embedding(c.embedding_json)
            if not emb:
                continue
            claim_sim = _cosine(q_emb, emb)
            item = c.item
            title_sim = _cosine(q_emb, item_embs.get(item.id, []))
            sim = max(claim_sim, title_sim)
            scored.append(
                (
                    sim,
                    f"- [{item.title}]({item.url}) (sim={sim:.2f})\n"
                    f"  Claim: {c.text}\n"
                    f"  Summary: {item.summary_one_liner}",
                )
            )

        # Also keep pure title/summary hits (helps "openai article" with no claim match)
        seen_items = {c.item_id for c in claims}
        for it in items:
            title_sim = _cosine(q_emb, item_embs.get(it.id, []))
            if it.id in seen_items and title_sim < SIM_FLOOR:
                continue
            scored.append(
                (
                    title_sim,
                    f"- [{it.title}]({it.url}) (sim={title_sim:.2f})\n"
                    f"  Summary: {it.summary_one_liner}",
                )
            )

        scored.sort(key=lambda x: x[0], reverse=True)
        # Dedupe identical blocks while preserving score order
        top: list[tuple[float, str]] = []
        seen_blocks: set[str] = set()
        for sim, block in scored:
            if block in seen_blocks:
                continue
            seen_blocks.add(block)
            top.append((sim, block))
            if len(top) >= top_k:
                break

        if not top:
            return ""

        small_corpus = len(claims) < SMALL_CORPUS_CLAIMS
        if not small_corpus and top[0][0] < SIM_FLOOR:
            return ""
        if small_corpus and top[0][0] < 0.15:
            # Still reject near-noise even for tiny corpora
            return ""

        # For larger corpora, filter under floor; for small, keep top-k as-is
        if not small_corpus:
            top = [(s, b) for s, b in top if s >= SIM_FLOOR]
            if not top:
                return ""

        return "\n".join(b for _, b in top)
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

    intent = detect_meta_intent(question)
    if intent:
        reply = handle_meta_intent(intent)
    else:
        context = retrieve_context(question, llm, settings)
        if not context:
            reply = (
                "No close match in your corpus. "
                "Try asking about content (a claim or topic from a save), "
                "or say: list my saves / are these related?"
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
