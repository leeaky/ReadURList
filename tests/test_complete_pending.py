import asyncio
from types import SimpleNamespace

from second_read.config import Settings
from second_read.db import Item, get_session, init_db
from second_read.ingest.complete import (
    complete_pending_bodies,
    complete_pending_bodies_sync,
)
from second_read.llm.base import LLMProvider
from second_read.rank import run as rank_run


class FakeLLM:
    def complete(
        self,
        prompt,
        *,
        model,
        system=None,
        schema=None,
        temperature=0.3,
    ) -> str:
        return (
            '{"title": "Filled", "snapshot": "Now we have a snapshot.",'
            ' "subject": "testing", "topics": ["tests"], "keywords": ["pytest"],'
            ' "priority": 4}'
        )


def test_complete_pending_fills_ready_item(tmp_path):
    db = f"sqlite:///{tmp_path / 't.db'}"
    init_db(db)
    session = get_session()
    try:
        session.add(
            Item(
                url="https://example.com/later",
                title="https://example.com/later",
                snapshot="not available",
                subject="not available",
                topics=[],
                keywords=[],
                extracted_text="Article body " * 40,
                priority=3,
                ingest_status="pending_body",
                note="HTTP 403",
            )
        )
        session.commit()
    finally:
        session.close()

    settings = Settings(
        telegram_bot_token="x",
        telegram_user_id=1,
        groq_api_key="x",
        database_url=db,
    )
    llm: LLMProvider = FakeLLM()  # type: ignore[assignment]
    done = complete_pending_bodies_sync(llm, settings)

    assert len(done) == 1
    assert done[0].ingest_status == "ready"
    assert done[0].snapshot == "Now we have a snapshot."
    assert done[0].subject == "testing"
    assert done[0].title == "Filled"


def test_complete_skips_stub_without_body(tmp_path):
    db = f"sqlite:///{tmp_path / 't.db'}"
    init_db(db)
    session = get_session()
    try:
        session.add(
            Item(
                url="https://example.com/empty",
                title="t",
                snapshot="not available",
                subject="not available",
                extracted_text="",
                ingest_status="pending_body",
            )
        )
        session.commit()
    finally:
        session.close()

    settings = Settings(
        telegram_bot_token="x",
        telegram_user_id=1,
        groq_api_key="x",
        database_url=db,
    )
    assert complete_pending_bodies_sync(FakeLLM(), settings) == []  # type: ignore[arg-type]


def test_complete_pending_uses_thread_and_continues_after_ack_failure(monkeypatch):
    items = [
        SimpleNamespace(id=1, title="First", url="https://example.com/first"),
        SimpleNamespace(id=2, title="Second", url="https://example.com/second"),
    ]
    thread_calls = []

    async def fake_to_thread(function, *args):
        thread_calls.append((function, args))
        return items

    class FakeBot:
        def __init__(self):
            self.sent = []

        async def send_message(self, **kwargs):
            self.sent.append(kwargs)
            if len(self.sent) == 1:
                raise RuntimeError("Telegram unavailable")

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)
    settings = Settings(
        telegram_bot_token="x",
        telegram_user_id=1,
        groq_api_key="x",
        database_url="sqlite://",
    )
    bot = FakeBot()
    llm = FakeLLM()

    count = asyncio.run(
        complete_pending_bodies(bot, llm, settings)  # type: ignore[arg-type]
    )

    assert count == 2
    assert thread_calls == [(complete_pending_bodies_sync, (llm, settings))]
    assert len(bot.sent) == 2


def test_digest_ranks_when_pending_completion_fails(monkeypatch):
    ranked = []

    async def fail_completion(*args):
        raise RuntimeError("Groq unavailable")

    def fake_persist_ranking():
        ranked.append(True)
        return []

    monkeypatch.setattr(rank_run, "complete_pending_bodies", fail_completion)
    monkeypatch.setattr(rank_run, "persist_ranking", fake_persist_ranking)
    settings = Settings(
        telegram_bot_token="x",
        telegram_user_id=1,
        groq_api_key="x",
        database_url="sqlite://",
    )

    sent = asyncio.run(
        rank_run.run_digest_job(object(), settings, FakeLLM())  # type: ignore[arg-type]
    )

    assert sent is False
    assert ranked == [True]


def test_complete_pending_canonicalizes_against_existing_subject(tmp_path):
    db = f"sqlite:///{tmp_path / 't.db'}"
    init_db(db)
    session = get_session()
    try:
        session.add(
            Item(
                url="https://example.com/ready",
                title="Ready",
                snapshot="s",
                subject="Claude Code",
                topics=["agents"],
                keywords=["k"],
                extracted_text="x" * 40,
                priority=3,
                ingest_status="ready",
            )
        )
        session.add(
            Item(
                url="https://example.com/later",
                title="later",
                snapshot="not available",
                subject="not available",
                topics=[],
                keywords=[],
                extracted_text="Article body " * 40,
                priority=3,
                ingest_status="pending_body",
            )
        )
        session.commit()
    finally:
        session.close()

    class CaseLLM:
        def complete(self, prompt, *, model, system=None, schema=None, temperature=0.3) -> str:
            assert "Claude Code" in prompt
            return (
                '{"title": "Filled", "snapshot": "Now we have a snapshot.",'
                ' "subject": "claude code", "topics": ["tests"], "keywords": ["pytest"],'
                ' "priority": 4}'
            )

    settings = Settings(
        telegram_bot_token="x",
        telegram_user_id=1,
        groq_api_key="x",
        database_url=db,
    )
    done = complete_pending_bodies_sync(CaseLLM(), settings)  # type: ignore[arg-type]
    assert done[0].subject == "Claude Code"


def test_digest_ranks_when_consolidation_fails(monkeypatch):
    ranked = []

    async def ok_completion(*args):
        return 0

    def boom(*args, **kwargs):
        raise RuntimeError("Groq consolidate unavailable")

    def fake_persist_ranking():
        ranked.append(True)
        return []

    monkeypatch.setattr(rank_run, "complete_pending_bodies", ok_completion)
    monkeypatch.setattr(rank_run, "maybe_consolidate_tags", boom)
    monkeypatch.setattr(rank_run, "persist_ranking", fake_persist_ranking)
    settings = Settings(
        telegram_bot_token="x",
        telegram_user_id=1,
        groq_api_key="x",
        database_url="sqlite://",
    )
    sent = asyncio.run(
        rank_run.run_digest_job(object(), settings, FakeLLM())  # type: ignore[arg-type]
    )
    assert sent is False
    assert ranked == [True]
