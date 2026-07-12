from __future__ import annotations

import logging

from telegram.ext import Application, CommandHandler, MessageHandler, filters

from second_read.bot.handlers import handle_message, handle_start
from second_read.config import Settings
from second_read.llm.base import LLMProvider
from second_read.ping import maybe_send_ping

logger = logging.getLogger(__name__)


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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Periodic ping checks with jitter inside the job
    interval = max(settings.ping_check_interval_minutes, 15) * 60
    if app.job_queue is not None:
        app.job_queue.run_repeating(
            maybe_send_ping,
            interval=interval,
            first=60,
            name="ping_scheduler",
        )
    else:
        logger.warning(
            "JobQueue unavailable — install python-telegram-bot[job-queue] for pings"
        )

    return app
