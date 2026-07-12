from __future__ import annotations

import logging
import sys

from second_read.bot import build_app
from second_read.config import get_settings
from second_read.db import init_db
from second_read.llm import GroqProvider


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        level=logging.INFO,
        stream=sys.stdout,
    )
    settings = get_settings()
    settings.ensure_data_dir()
    init_db(settings.database_url)

    llm = GroqProvider(
        api_key=settings.groq_api_key,
        embed_model=settings.model_embed,
    )
    app = build_app(settings, llm)

    logging.getLogger(__name__).info(
        "Second Read starting (allowlisted user=%s, llm=groq)",
        settings.telegram_user_id,
    )
    app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
