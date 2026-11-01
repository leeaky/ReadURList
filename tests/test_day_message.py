from datetime import datetime, timedelta, timezone

from readurlist.db import Item, get_session, init_db
from readurlist.rank.run import format_digest, persist_ranking

DAY1 = datetime(2026, 11, 1, 7, 0, tzinfo=timezone.utc)
DAY2 = DAY1 + timedelta(days=1)
SITE = "https://readurlist.example"


def _add(url: str, subject: str, saved: datetime, words: int | None = 1000,
         status: str = "ready") -> int:
    session = get_session()
    item = Item(url=url, title=f"Title {url[-1]}", snapshot="s", subject=subject, topics=[],
                keywords=[], extracted_text="x", priority=3, ingest_status=status,
                created_at=saved, word_count=words)
    session.add(item)
    session.commit()
    item_id = item.id
    session.close()
    return item_id


def test_message_has_short_and_long_sections(tmp_path):
    init_db(f"sqlite:///{tmp_path / 't.db'}")
    _add("https://example.com/a", "a", DAY1)
    _add("https://example.com/l", "b", DAY1, words=5000)
    persist_ranking(now=DAY1)
    text = format_digest(DAY1.date(), SITE)
    assert text.index("Short reads") < text.index("Title a") < text.index("Long read")
    assert text.index("Long read") < text.index("Title l")
    assert "Why: You keep saving a (1 unread in a)\n" in text


def test_empty_long_section_points_to_unfetched(tmp_path):
    init_db(f"sqlite:///{tmp_path / 't.db'}")
    _add("https://example.com/a", "a", DAY1)
    _add("https://example.com/p1", "", DAY1, words=None, status="pending_body")
    _add("https://example.com/p2", "", DAY1, words=None, status="pending_body")
    persist_ranking(now=DAY1)
    text = format_digest(DAY1.date(), SITE)
    assert "No long read ready. 2 papers are waiting on Unfetched: https://readurlist.example/unfetched" in text


def test_fallen_off_note_lists_each_link_with_its_cause(tmp_path):
    init_db(f"sqlite:///{tmp_path / 't.db'}")
    read = _add("https://example.com/r", "a", DAY1)
    old = _add("https://example.com/o", "c", DAY1 - timedelta(days=3))
    persist_ranking(now=DAY1)
    session = get_session()
    session.get(Item, read).read_at = DAY2
    session.commit()
    session.close()
    for n in range(3):
        _add(f"https://example.com/n{n}", f"new{n}", DAY2)
    persist_ranking(now=DAY2)

    text = format_digest(DAY2.date(), SITE)
    note = text[text.index("Fallen off"):]
    assert "https://example.com/r — you read it" in note
    assert "https://example.com/o — outscored by newer saves" in note


def test_message_gives_reasons_in_words_without_points(tmp_path):
    init_db(f"sqlite:///{tmp_path / 't.db'}")
    read = _add("https://example.com/r", "a", DAY1)
    _add("https://example.com/o", "c", DAY1 - timedelta(days=3))
    persist_ranking(now=DAY1)
    session = get_session()
    session.get(Item, read).read_at = DAY2
    session.commit()
    session.close()
    for n in range(3):
        _add(f"https://example.com/n{n}", f"new{n}", DAY2)
    persist_ranking(now=DAY2)

    text = format_digest(DAY2.date(), SITE)
    assert "Fallen off" in text
    assert "points" not in text
    assert "subject " not in text and "recency" not in text


def test_daily_message_has_no_buttons(tmp_path):
    import asyncio

    from readurlist.config import Settings
    from readurlist.rank.run import run_digest_job

    init_db(f"sqlite:///{tmp_path / 't.db'}")
    _add("https://example.com/a", "a", datetime.now(timezone.utc))

    class FakeBot:
        def __init__(self):
            self.sent = []

        async def send_message(self, **kwargs):
            self.sent.append(kwargs)

    bot = FakeBot()
    settings = Settings(telegram_bot_token="x", telegram_user_id=1, groq_api_key="x",
                        database_url="sqlite://", site_url=SITE)
    assert asyncio.run(run_digest_job(bot, settings))  # type: ignore[arg-type]
    assert len(bot.sent) == 1
    assert bot.sent[0].get("reply_markup") is None
    assert "Short reads" in bot.sent[0]["text"]
