from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

from readurlist.config import Settings
from readurlist.db import (
    DailyPick,
    DigestRun,
    FallenOff,
    Item,
    get_session,
)
from readurlist.ingest.complete import complete_pending_bodies
from readurlist.llm.base import LLMProvider
from readurlist.rank.digest import should_send_digest
from readurlist.rank.score import RankItem, build_day_list
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
        restored_at=row.restored_at,
        word_count=row.word_count,
    )


def persist_ranking(*, now: datetime | None = None) -> list[DailyPick]:
    """Rebuild today's daily_picks. No Telegram."""
    now = now or datetime.now().astimezone()
    today = now.date()
    session = get_session()
    try:
        items = (
            session.query(Item)
            .filter(Item.ingest_status == "ready")
            .all()
        )
        rank_items = [_to_rank_item(i) for i in items]
        by_id = {i.id: i for i in items}

        session.query(DailyPick).filter(DailyPick.run_on == today).delete()
        session.query(FallenOff).filter(FallenOff.run_on == today).delete()
        day = build_day_list(rank_items, now=now)
        stored: list[DailyPick] = []
        for pick in day.picks:
            row = DailyPick(
                run_on=today,
                item_id=pick.item_id,
                rank=pick.rank,
                score=pick.score,
                reason=pick.reason,
                subject_points=pick.subject_points,
                recency_points=pick.recency_points,
                section=pick.section,
            )
            session.add(row)
            stored.append(row)

        today_ids = {p.item_id for p in day.picks}
        for prev in _previous_picks(session, today):
            if prev.item_id in today_ids:
                continue
            item = by_id.get(prev.item_id)
            after = day.scores.get(prev.item_id)
            session.add(
                FallenOff(
                    run_on=today,
                    item_id=prev.item_id,
                    cause=_fall_cause(item, prev.item_id, day.capped),
                    points_before=prev.score,
                    points_after=after.score if after else None,
                )
            )
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


def _previous_picks(session, today: date) -> list[DailyPick]:
    """The most recent list before today (normally yesterday's)."""
    last = (
        session.query(DailyPick.run_on)
        .filter(DailyPick.run_on < today)
        .order_by(DailyPick.run_on.desc())
        .limit(1)
        .scalar()
    )
    if last is None:
        return []
    return session.query(DailyPick).filter(DailyPick.run_on == last).all()


def _fall_cause(item: Item | None, item_id: int, capped: set[int]) -> str:
    if item is None:
        return "gone"  # deleted, or no longer ready
    if item.read_at is not None:
        return "read"
    if item.skipped_at is not None:
        return "skipped"
    if item_id in capped:
        return "subject_full"
    return "outscored"


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


FALL_CAUSES = {
    "read": "you read it",
    "skipped": "you skipped it",
    "outscored": "outscored by newer saves",
    "subject_full": "its subject already has two picks",
    "gone": "no longer in the pile",
}


def _fall_line(row: FallenOff, item: Item | None) -> str:
    where = item.url if item else f"item {row.item_id}"
    line = f"{where} — {FALL_CAUSES.get(row.cause, row.cause)}"
    if row.points_after is not None:
        line += f" ({row.points_before:g} → {row.points_after} points)"
    return line


def _pick_line(n: int, pick: DailyPick, item: Item) -> str:
    title = item.title or item.url
    snap = (item.snapshot or "").split("\n")[0]
    if len(snap) > 240:
        snap = snap[:237] + "…"
    return f"{n}. {title}\n{snap}\nWhy: {pick.reason}\n"


def format_digest(run_on: date, site_url: str) -> tuple[str, InlineKeyboardMarkup | None]:
    """The day's list: short section, long section (or where the papers are), fallen off."""
    session = get_session()
    try:
        picks = (
            session.query(DailyPick)
            .filter(DailyPick.run_on == run_on)
            .order_by(DailyPick.rank)
            .all()
        )
        if not picks:
            return "No unread articles to rank today.", None
        lines = ["Today's reads\n"]
        buttons: list[list[InlineKeyboardButton]] = []
        n = 0
        for section, heading in (("short", "Short reads"), ("long", "Long read")):
            lines.append(heading)
            rows = [p for p in picks if (p.section or "short") == section]
            for pick in rows:
                item = session.get(Item, pick.item_id)
                if item is None:
                    continue
                n += 1
                lines.append(_pick_line(n, pick, item))
                buttons.append(
                    [
                        InlineKeyboardButton(f"Mark read · {n}", callback_data=f"read:{item.id}"),
                        InlineKeyboardButton(f"Skip · {n}", callback_data=f"skip:{item.id}"),
                    ]
                )
            if section == "long" and not rows:
                waiting = (
                    session.query(Item).filter(Item.ingest_status == "pending_body").count()
                )
                base = (site_url or "").rstrip("/")
                where = f": {base}/unfetched" if base else ""
                lines.append(f"No long read ready. {waiting} papers are waiting on Unfetched{where}\n")
        fallen = session.query(FallenOff).filter(FallenOff.run_on == run_on).all()
        if fallen:
            lines.append("Fallen off since the last list")
            lines += [_fall_line(row, session.get(Item, row.item_id)) for row in fallen]
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

    text, markup = format_digest(today, settings.site_url)
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
