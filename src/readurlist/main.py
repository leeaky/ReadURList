from __future__ import annotations

import logging
import sys

from readurlist.bot import build_app
from readurlist.config import get_settings
from readurlist.db import init_db
from readurlist.llm import GroqProvider


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        level=logging.INFO,
        stream=sys.stdout,
    )
    settings = get_settings()
    settings.ensure_data_dir()
    init_db(settings.database_url)

    llm = GroqProvider(api_key=settings.groq_api_key)
    app = build_app(settings, llm)

    logging.getLogger(__name__).info(
        "ReadURList starting (allowlisted user=%s, llm=groq, digest=%02d:00)",
        settings.telegram_user_id,
        settings.digest_hour,
    )
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
