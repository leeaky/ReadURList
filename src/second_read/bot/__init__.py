from __future__ import annotations

import logging
from datetime import datetime, time as dt_time

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from second_read.bot.handlers import (
    handle_digest,
    handle_message,
    handle_read_callback,
    handle_start,
)
from second_read.config import Settings
from second_read.llm.base import LLMProvider
from second_read.rank.run import run_digest_job

logger = logging.getLogger(__name__)


async def _scheduled_digest(context) -> None:
    settings: Settings = context.application.bot_data["settings"]
    llm: LLMProvider = context.application.bot_data["llm"]
    await run_digest_job(context.bot, settings, llm, force=False)


def build_app(settings: Settings, llm: LLMProvider) -> Application:
    app = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .build()
    )
    app.bot_data["settings"] = settings
    app.bot_data["llm"] = llm
    app.bot_data["chat_id"] = settings.telegram_user_id

    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CommandHandler("digest", handle_digest))
    app.add_handler(CallbackQueryHandler(handle_read_callback, pattern=r"^read:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    if app.job_queue is not None:
        tz = datetime.now().astimezone().tzinfo
        app.job_queue.run_daily(
            _scheduled_digest,
            time=dt_time(hour=settings.digest_hour, minute=0, tzinfo=tz),
            name="daily_digest",
        )
        logger.info("Daily digest scheduled at %02d:00 local", settings.digest_hour)
    else:
        logger.warning(
            "JobQueue unavailable — install python-telegram-bot[job-queue] for digest"
        )

    return app
