from second_read.config import Settings
from second_read.db import Item, get_session, init_db
from second_read.ingest import ingest_url
from second_read.ingest.extract import ExtractError, FetchError
from second_read.llm.base import LLMProvider


class CountingLLM:
    def __init__(self) -> None:
        self.calls = 0

    def complete(self, prompt, *, model, system=None, schema=None, temperature=0.3) -> str:
        self.calls += 1
        raise AssertionError("LLM must not be called for stubs")


def _settings(db: str) -> Settings:
    return Settings(
        telegram_bot_token="x",
        telegram_user_id=1,
        groq_api_key="x",
        database_url=db,
    )


def test_fetch_error_saves_pending_stub_without_llm(tmp_path, monkeypatch):
    db = f"sqlite:///{tmp_path / 't.db'}"
    init_db(db)

    def boom(url: str, timeout: float = 30.0):
        raise FetchError("Site rate-limited or unavailable (HTTP 429).", status_code=429)

    monkeypatch.setattr("second_read.ingest.extract_article", boom)
    llm: LLMProvider = CountingLLM()  # type: ignore[assignment]
    url = "https://example.com/blocked"

    item, created = ingest_url(url, llm, _settings(db))

    assert created is True
    assert item.ingest_status == "pending_body"
    assert item.title == url
    assert item.snapshot == "not available"
    assert item.subject == "not available"
    assert item.topics == []
    assert item.keywords == []
    assert item.extracted_text == ""
    assert "429" in (item.note or "") or "rate-limited" in (item.note or "").lower()
    assert llm.calls == 0  # type: ignore[attr-defined]


def test_extract_error_keeps_headline(tmp_path, monkeypatch):
    db = f"sqlite:///{tmp_path / 't.db'}"
    init_db(db)

    def boom(url: str, timeout: float = 30.0):
        raise ExtractError("Could not extract enough article text from URL", title="Nice Headline")

    monkeypatch.setattr("second_read.ingest.extract_article", boom)
    llm: LLMProvider = CountingLLM()  # type: ignore[assignment]

    item, created = ingest_url("https://example.com/short", llm, _settings(db))

    assert created is True
    assert item.ingest_status == "pending_body"
    assert item.title == "Nice Headline"
    assert item.snapshot == "not available"
    assert llm.calls == 0  # type: ignore[attr-defined]


def test_stub_dedup_returns_existing(tmp_path, monkeypatch):
    db = f"sqlite:///{tmp_path / 't.db'}"
    init_db(db)
    calls = {"n": 0}

    def boom(url: str, timeout: float = 30.0):
        calls["n"] += 1
        raise FetchError("Could not fetch page (HTTP 403).", status_code=403)

    monkeypatch.setattr("second_read.ingest.extract_article", boom)
    llm: LLMProvider = CountingLLM()  # type: ignore[assignment]
    url = "https://example.com/once"
    first, c1 = ingest_url(url, llm, _settings(db))
    second, c2 = ingest_url(url, llm, _settings(db))
    assert c1 is True and c2 is False
    assert first.id == second.id
    assert calls["n"] == 1
