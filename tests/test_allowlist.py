import asyncio
from types import SimpleNamespace

from readurlist.bot.handlers import handle_message
from readurlist.config import Settings


class FakeMessage:
    def __init__(self, text: str) -> None:
        self.text = text
        self.replies: list[str] = []

    async def reply_text(self, text: str, **kwargs) -> None:
        self.replies.append(text)


def _run(user_id: int, monkeypatch) -> tuple[FakeMessage, list[str]]:
    settings = Settings(telegram_bot_token="x", telegram_user_id=1, groq_api_key="x")
    saved: list[str] = []

    def fake_ingest(url, llm, settings):
        saved.append(url)
        return SimpleNamespace(ingest_status="ready", title="t", snapshot="s"), True

    monkeypatch.setattr("readurlist.bot.handlers.ingest_url", fake_ingest)
    message = FakeMessage("https://example.com/a")
    update = SimpleNamespace(effective_user=SimpleNamespace(id=user_id), message=message)
    context = SimpleNamespace(
        application=SimpleNamespace(bot_data={"settings": settings, "llm": None})
    )
    asyncio.run(handle_message(update, context))
    return message, saved


def test_other_user_gets_no_reply_and_nothing_is_saved(monkeypatch):
    message, saved = _run(user_id=2, monkeypatch=monkeypatch)
    assert message.replies == []
    assert saved == []


def test_allowlisted_user_link_is_saved_and_answered(monkeypatch):
    message, saved = _run(user_id=1, monkeypatch=monkeypatch)
    assert saved == ["https://example.com/a"]
    assert message.replies
