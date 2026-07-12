from __future__ import annotations

import json
import logging

from second_read.config import Settings
from second_read.db import Claim, Item, get_session
from second_read.ingest.extract import extract_article
from second_read.ingest.summarize import summarize_and_claim
from second_read.llm.base import LLMProvider

logger = logging.getLogger(__name__)


def ingest_url(url: str, llm: LLMProvider, settings: Settings) -> Item:
    """Extract, summarize, persist item + claims with embeddings. Returns Item."""
    title_hint, text = extract_article(url)
    result = summarize_and_claim(
        llm,
        model=settings.model_ingest,
        url=url,
        title_hint=title_hint,
        text=text,
    )

    embeddings: list[list[float]] = []
    if result.claims:
        embeddings = llm.embed(result.claims, model=settings.model_embed)

    session = get_session()
    try:
        existing = session.query(Item).filter_by(url=url).one_or_none()
        if existing:
            session.expunge(existing)
            return existing

        item = Item(
            url=url,
            title=result.title,
            extracted_text=text,
            summary_one_liner=result.summary_one_liner,
        )
        session.add(item)
        session.flush()

        for i, claim_text in enumerate(result.claims):
            emb = embeddings[i] if i < len(embeddings) else None
            session.add(
                Claim(
                    item_id=item.id,
                    text=claim_text,
                    embedding_json=json.dumps(emb) if emb is not None else None,
                )
            )
        session.commit()
        session.refresh(item)
        # Detach so callers can use attributes after session closes
        session.expunge(item)
        return item
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
