from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

from readurlist.config import Settings
from readurlist.db import (
    DailyPick,
    DigestRun,
    Item,
    get_session,
)
from readurlist.ingest.complete import complete_pending_bodies
from readurlist.llm.base import LLMProvider
from readurlist.rank.digest import should_send_digest
from readurlist.rank.score import RankItem, score_unread
from readurlist.tags.consolidate import maybe_consolidate_tags

logger = logging.getLogger(__name__)


def _to_rank_item(row: Item) -> RankItem:
    return RankItem(
        id=row.id,
        subject=row.subject or "",
        topics=list(row.topics or []),
        keywords=list(row.keywords or []),
        created_at=row.created_at or datetime.now().astimezone(),
        read_at=row.read_at,
        priority=row.priority or 3,
        skipped_at=row.skipped_at,
    )


def persist_ranking(*, now: datetime | None = None) -> list[DailyPick]:
    """Rebuild today's daily_picks. No Telegram."""
    now = now or datetime.now().astimezone()
    today = now.date()
    session = get_session()
    try:
        items = (
            session.query(Item)
            .filter(Item.ingest_status != "pending_body")
            .all()
        )
        rank_items = [_to_rank_item(i) for i in items]
        by_id = {i.id: i for i in items}

        session.query(DailyPick).filter(DailyPick.run_on == today).delete()
        picks = score_unread(rank_items, now=now, top_n=5)
        stored: list[DailyPick] = []
        for pick in picks:
            row = DailyPick(
                run_on=today,
                item_id=pick.item_id,
                rank=pick.rank,
                score=pick.score,
                reason=pick.reason,
            )
            session.add(row)
            stored.append(row)
            _ = by_id.get(pick.item_id)
        session.commit()
        for row in stored:
            session.refresh(row)
            session.expunge(row)
        return stored
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _existing_digest_run(today: date) -> date | None:
    session = get_session()
    try:
        run = session.get(DigestRun, today)
        return run.run_on if run else None
    finally:
        session.close()


def _record_digest_run(today: date) -> None:
    session = get_session()
    try:
        if session.get(DigestRun, today) is None:
            session.add(DigestRun(run_on=today, sent_at=datetime.now().astimezone()))
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def format_digest(picks: list[DailyPick]) -> tuple[str, InlineKeyboardMarkup | None]:
    if not picks:
        return "No unread articles to rank today.", None
    session = get_session()
    try:
        lines = ["Today's reads\n"]
        buttons: list[list[InlineKeyboardButton]] = []
        for pick in sorted(picks, key=lambda p: p.rank):
            item = session.get(Item, pick.item_id)
            if item is None:
                continue
            title = item.title or item.url
            snap = (item.snapshot or "").split("\n")[0]
            if len(snap) > 240:
                snap = snap[:237] + "…"
            lines.append(f"{pick.rank}. {title}\n{snap}\nWhy: {pick.reason}\n")
            buttons.append(
                [
                    InlineKeyboardButton(
                        f"Mark read · {pick.rank}",
                        callback_data=f"read:{item.id}",
                    ),
                    InlineKeyboardButton(
                        f"Skip · {pick.rank}",
                        callback_data=f"skip:{item.id}",
                    ),
                ]
            )
        markup = InlineKeyboardMarkup(buttons) if buttons else None
        return "\n".join(lines).strip(), markup
    finally:
        session.close()


async def run_digest_job(
    bot: Bot,
    settings: Settings,
    llm: LLMProvider | None = None,
    *,
    force: bool = False,
) -> bool:
    """Rank, persist, send Telegram digest at most once per day.

    Returns True if a digest message was sent.
    """
    if llm is not None:
        try:
            await complete_pending_bodies(bot, llm, settings)
        except Exception:
            logger.exception("Pending-body completion failed; continuing with digest")

    if llm is not None:
        try:
            await asyncio.to_thread(maybe_consolidate_tags, llm, settings)
        except Exception:
            logger.exception("Tag consolidation failed; continuing with digest")

    today = date.today()
    picks = persist_ranking()
    if not picks:
        logger.info("No unread picks — not sending a digest")
        return False
    existing = _existing_digest_run(today)
    if not force and not should_send_digest(existing_run_on=existing, today=today):
        logger.info("Digest already sent for %s — skipping Telegram", today)
        return False
    if force and existing is not None:
        logger.info("Force digest: ranking updated, Telegram suppressed (already sent %s)", today)
        return False

    text, markup = format_digest(picks)
    await bot.send_message(
        chat_id=settings.telegram_user_id,
        text=text,
        reply_markup=markup,
        disable_web_page_preview=True,
    )
    _record_digest_run(today)
    logger.info("Sent digest for %s (%s picks)", today, len(picks))
    return True


def main() -> None:
    """CLI: `python -m readurlist.rank` — rank now; send digest if not yet today."""
    import asyncio

    from telegram import Bot

    from readurlist.config import get_settings
    from readurlist.db import init_db
    from readurlist.llm import GroqProvider

    settings = get_settings()
    init_db(settings.database_url)
    bot = Bot(settings.telegram_bot_token)
    llm = GroqProvider(api_key=settings.groq_api_key)
    sent = asyncio.run(run_digest_job(bot, settings, llm, force=False))
    print("digest sent" if sent else "ranked; digest already sent today")
