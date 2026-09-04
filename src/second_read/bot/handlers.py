from __future__ import annotations

import asyncio
import logging

from second_read.db import mark_item_read, mark_item_skipped
from second_read.ingest import INGEST_PENDING_BODY, ingest_url
from second_read.ingest.extract import find_urls
from second_read.rank.run import run_digest_job

logger = logging.getLogger(__name__)


def format_stub_ack(site_url: str, *, prefix: str = "") -> str:
    base = (site_url or "").rstrip("/")
    if base:
        link = f"{base}/unfetched"
        body = (
            "Saved, but the article could not be retrieved. "
            f"Paste the text or a PDF on the Unfetched page: {link}"
        )
    else:
        body = (
            "Saved, but the article could not be retrieved. "
            "Paste the text or a PDF on the website Unfetched page."
        )
    return f"{prefix}{body}"


async def handle_message(update, context) -> None:
    settings = context.application.bot_data["settings"]
    llm = context.application.bot_data["llm"]

    if not update.effective_user or not update.message or not update.message.text:
        return

    if update.effective_user.id != settings.telegram_user_id:
        logger.warning("Ignored message from non-allowlisted user %s", update.effective_user.id)
        return

    text = update.message.text.strip()
    urls = find_urls(text)

    if urls:
        total = len(urls)
        for index, url in enumerate(urls, 1):
            prefix = f"{index}/{total} " if total > 1 else ""
            await update.message.reply_text(f"{prefix}Saving…")
            try:
                item, created = await asyncio.to_thread(ingest_url, url, llm, settings)
            except Exception as exc:
                logger.exception("Ingest failed for %s", url)
                await update.message.reply_text(f"{prefix}Couldn't save that URL: {exc}")
                continue

            if item.ingest_status == INGEST_PENDING_BODY:
                await update.message.reply_text(
                    format_stub_ack(settings.site_url, prefix=prefix)
                )
                continue

            title = _escape_md(item.title or url)
            snapshot = _escape_md(item.snapshot or "")
            status = "" if created else "Already saved.\n"
            ack = f"{prefix}{status}*{title}*\n{snapshot}".strip()
            await update.message.reply_text(ack, parse_mode="Markdown")
        return

    await update.message.reply_text(
        "Paste one or more http(s) URLs to save them.\n"
        "Browse and mark read on the website. Send /digest to run today's ranking now."
    )


async def handle_start(update, context) -> None:
    settings = context.application.bot_data["settings"]
    if not update.effective_user or update.effective_user.id != settings.telegram_user_id:
        return
    await update.message.reply_text(
        "ReadURList is listening.\n"
        "• Paste a URL (or several) to save a snapshot.\n"
        "• Daily digest: ranked unread reads, with Mark read buttons.\n"
        "• Browse the corpus on the website (see README)."
    )


async def handle_digest(update, context) -> None:
    settings = context.application.bot_data["settings"]
    llm = context.application.bot_data["llm"]
    if not update.effective_user or update.effective_user.id != settings.telegram_user_id:
        return
    await update.message.reply_text("Running ranking…")
    try:
        sent = await run_digest_job(context.bot, settings, llm, force=True)
    except Exception as exc:
        logger.exception("Manual digest failed")
        await update.message.reply_text(f"Digest failed: {exc}")
        return
    if sent:
        return
    await update.message.reply_text("Ranking updated. Digest already sent today — not sending again.")


async def handle_read_callback(update, context) -> None:
    settings = context.application.bot_data["settings"]
    query = update.callback_query
    if not query or not query.data:
        return
    if not update.effective_user or update.effective_user.id != settings.telegram_user_id:
        await query.answer("Not allowed.")
        return
    if not query.data.startswith("read:"):
        await query.answer()
        return
    try:
        item_id = int(query.data.split(":", 1)[1])
    except ValueError:
        await query.answer("Bad id")
        return
    item = mark_item_read(item_id, read=True)
    if item is None:
        await query.answer("Not found")
        return
    await query.answer("Marked read")
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        logger.debug("Could not clear markup after mark-read")


async def handle_skip_callback(update, context) -> None:
    settings = context.application.bot_data["settings"]
    query = update.callback_query
    if not query or not query.data:
        return
    if not update.effective_user or update.effective_user.id != settings.telegram_user_id:
        await query.answer("Not allowed.")
        return
    if not query.data.startswith("skip:"):
        await query.answer()
        return
    try:
        item_id = int(query.data.split(":", 1)[1])
    except ValueError:
        await query.answer("Bad id")
        return
    item = mark_item_skipped(item_id, skipped=True)
    if item is None:
        await query.answer("Not found")
        return
    await query.answer("Skipped")


def _escape_md(text: str) -> str:
    """Minimal Markdown escaping for Telegram legacy Markdown."""
    for ch in ("_", "*", "`", "["):
        text = text.replace(ch, f"\\{ch}")
    return text
