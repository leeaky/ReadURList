from readurlist.bot.handlers import format_stub_ack


def test_format_stub_ack_includes_unfetched_link():
    text = format_stub_ack("https://readurlist.example")
    assert "could not be retrieved" in text.lower() or "could not retrieve" in text.lower()
    assert "https://readurlist.example/unfetched" in text


def test_format_stub_ack_without_site_url():
    text = format_stub_ack("")
    assert "unfetched" in text.lower()
    assert "http" not in text  # no broken link


def test_held_page_reply_says_held_and_where_to_release(monkeypatch):
    import asyncio
    from types import SimpleNamespace

    from readurlist.bot.handlers import handle_message
    from readurlist.config import Settings

    settings = Settings(
        telegram_bot_token="x", telegram_user_id=1, groq_api_key="x",
        site_url="https://readurlist.example",
    )
    monkeypatch.setattr(
        "readurlist.bot.handlers.ingest_url",
        lambda url, llm, s: (SimpleNamespace(ingest_status="held", title="t", snapshot=""), True),
    )
    class FakeMessage:
        text = "https://example.com/a"
        replies: list[str] = []

        async def reply_text(self, text, **kwargs):
            self.replies.append(text)

    message = FakeMessage()
    update = SimpleNamespace(effective_user=SimpleNamespace(id=1), message=message)
    context = SimpleNamespace(application=SimpleNamespace(bot_data={"settings": settings, "llm": None}))
    asyncio.run(handle_message(update, context))

    reply = message.replies[-1]
    assert "held" in reply.lower()
    assert "https://readurlist.example/unfetched" in reply
