from __future__ import annotations

import asyncio
import logging

from telegram import Bot

from second_read.config import Settings
from second_read.db import Item, get_session
from second_read.ingest import INGEST_PENDING_BODY, INGEST_READY
from second_read.ingest.summarize import summarize_article
from second_read.llm.base import LLMProvider
from second_read.tags.vocab import load_vocabulary

logger = logging.getLogger(__name__)


def complete_pending_bodies_sync(llm: LLMProvider, settings: Settings) -> list[Item]:
    session = get_session()
    completed: list[Item] = []
    try:
        rows = (
            session.query(Item)
            .filter(Item.ingest_status == INGEST_PENDING_BODY)
            .all()
        )
        for row in rows:
            body = (row.extracted_text or "").strip()
            if not body:
                continue
            try:
                vocab = load_vocabulary()
                result = summarize_article(
                    llm,
                    model=settings.model_ingest,
                    url=row.url,
                    title_hint=row.title or row.url,
                    text=body,
                    existing_subjects=vocab.subjects,
                    existing_topics=vocab.topics,
                )
            except Exception as exc:
                logger.exception("Complete pending failed for item %s", row.id)
                row.note = f"complete failed: {exc}"[:500]
                session.commit()
                continue
            row.title = result.title
            row.snapshot = result.snapshot
            row.subject = result.subject
            row.topics = list(result.topics)
            row.keywords = list(result.keywords)
            row.priority = result.priority
            row.ingest_status = INGEST_READY
            session.commit()
            session.refresh(row)
            session.expunge(row)
            completed.append(row)
        return completed
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def complete_pending_bodies(
    bot: Bot,
    llm: LLMProvider,
    settings: Settings,
) -> int:
    done = await asyncio.to_thread(complete_pending_bodies_sync, llm, settings)
    for item in done:
        title = item.title or item.url
        try:
            await bot.send_message(
                chat_id=settings.telegram_user_id,
                text=f"Filled in {title} from your paste/PDF.",
                disable_web_page_preview=True,
            )
        except Exception:
            logger.exception("Failed to send completion ack for item %s", item.id)
    return len(done)
