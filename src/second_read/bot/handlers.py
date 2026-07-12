from __future__ import annotations

import asyncio
import logging

from second_read.connect import connect_new_claims
from second_read.converse import answer_from_corpus
from second_read.db import Claim, get_session
from second_read.ingest import ingest_url
from second_read.ingest.extract import find_urls

logger = logging.getLogger(__name__)


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
        url = urls[0]
        await update.message.reply_text("Saving…")
        try:
            item = await asyncio.to_thread(ingest_url, url, llm, settings)
        except Exception as exc:
            logger.exception("Ingest failed for %s", url)
            await update.message.reply_text(f"Couldn't save that URL: {exc}")
            return

        ack = f"*{_escape_md(item.title)}*\n{_escape_md(item.summary_one_liner)}"
        await update.message.reply_text(ack, parse_mode="Markdown")

        session = get_session()
        try:
            claim_ids = [
                c.id for c in session.query(Claim).filter_by(item_id=item.id).all()
            ]
        finally:
            session.close()

        if claim_ids:
            try:
                created = await asyncio.to_thread(
                    connect_new_claims, claim_ids, llm, settings
                )
                logger.info(
                    "Connected %s new relationships for item %s",
                    len(created),
                    item.id,
                )
            except Exception:
                logger.exception("Connect failed for item %s", item.id)
        return

    try:
        reply = await asyncio.to_thread(
            answer_from_corpus,
            text,
            llm,
            settings,
            telegram_message_id=update.message.message_id,
        )
    except Exception as exc:
        logger.exception("Converse failed")
        await update.message.reply_text(f"Something went wrong answering: {exc}")
        return

    await update.message.reply_text(reply, disable_web_page_preview=True)


async def handle_start(update, context) -> None:
    settings = context.application.bot_data["settings"]
    if not update.effective_user or update.effective_user.id != settings.telegram_user_id:
        return
    await update.message.reply_text(
        "Second Read is listening.\n"
        "• Paste a URL to save it (short ack only).\n"
        "• Ask anything about your corpus anytime.\n"
        "• I'll ping when a genuine connection appears — silence otherwise."
    )


def _escape_md(text: str) -> str:
    """Minimal Markdown escaping for Telegram legacy Markdown."""
    for ch in ("_", "*", "`", "["):
        text = text.replace(ch, f"\\{ch}")
    return text
