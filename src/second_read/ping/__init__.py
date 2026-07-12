from __future__ import annotations

import logging
import random
from datetime import datetime

from telegram.ext import ContextTypes

from second_read.config import Settings
from second_read.db import Item, Ping, Relationship, get_session
from second_read.llm.base import LLMProvider
from second_read.ping.compose import compose_ping, format_ping_message
from second_read.ping.select import (
    mark_checked,
    pings_sent_today,
    recently_checked,
    select_relationship,
    within_quiet_hours,
)

logger = logging.getLogger(__name__)

META_LAST_CHECK = "last_ping_check"


async def maybe_send_ping(
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Job callback: send at most one ping if a genuine hook exists."""
    settings: Settings = context.application.bot_data["settings"]
    llm: LLMProvider = context.application.bot_data["llm"]
    chat_id: int = context.application.bot_data["chat_id"]

    # Jitter: randomly skip ~40% of wakeups so timing feels unpredictable
    if random.random() < 0.4:
        logger.debug("Ping wakeup skipped by jitter")
        return

    if not within_quiet_hours(settings.quiet_hours_start, settings.quiet_hours_end):
        return

    if recently_checked(META_LAST_CHECK, settings.ping_check_interval_minutes):
        return
    mark_checked(META_LAST_CHECK)

    if pings_sent_today() >= settings.max_pings_per_day:
        return

    rel = select_relationship()
    if rel is None:
        logger.info("No qualifying relationship for ping — staying silent")
        return

    # Re-load relationship with claims/items in a fresh session for compose
    session = get_session()
    try:
        rel = session.get(Relationship, rel.id)
        if rel is None or rel.surfaced_at is not None:
            return
        # Touch relationships for lazy load
        _ = rel.claim_a.item.title
        _ = rel.claim_b.item.title

        content = compose_ping(llm, settings, rel)
        text = format_ping_message(content, rel)

        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )

        now = datetime.now()
        rel.surfaced_at = now
        ping = Ping(
            relationship_id=rel.id,
            hook=content.hook,
            analysis=content.analysis,
            question=content.question,
            sent_at=now,
        )
        session.add(ping)

        for claim in (rel.claim_a, rel.claim_b):
            item = session.get(Item, claim.item_id)
            if item:
                item.surfaced_count = (item.surfaced_count or 0) + 1

        session.commit()
        logger.info("Sent ping for relationship %s (%s)", rel.id, rel.type)
    except Exception:
        session.rollback()
        logger.exception("Failed to send ping")
    finally:
        session.close()
