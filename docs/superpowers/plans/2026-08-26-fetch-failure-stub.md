# Fetch-failure stub + Unfetched fill-in Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When article fetch/extract fails, save a stub corpus item, let the user paste text or a PDF on `/unfetched`, and complete snapshot/tags once a day on the NUC with Groq.

**Architecture:** Add `ingest_status` (`ready` | `pending_body`) on `items`. Failed Telegram ingest inserts a stub (no Groq). The Vercel site lists stubs on `/unfetched` and writes `extracted_text` from paste/PDF. The existing daily digest job (and `/digest`) first completes any `pending_body` rows that have body text, then ranks only `ready` items.

**Tech Stack:** Python 3.11+, SQLAlchemy, pytest, python-telegram-bot, Groq (NUC only), Next.js 15, Supabase JS, PDF text extraction on Vercel (`unpdf`).

## Global Constraints

- Groq stays on the NUC only — no `GROQ_API_KEY` on Vercel.
- LLM runs only after the user provides text or PDF (`extracted_text` non-empty).
- Completion cadence: once daily with digest / `/digest` — no continuous poller.
- Stub markers: `snapshot` and `subject` literal string `not available`; `topics`/`keywords` empty lists.
- Hide `pending_body` from Today, Unread, All, Topics, Clusters; Unfetched owns them.
- Dedup unchanged: same URL returns existing row; user completes via Unfetched.

## File structure

| File | Responsibility |
|------|----------------|
| `supabase/migrations/20260826000000_ingest_status.sql` | Add `ingest_status` column |
| `src/second_read/db/__init__.py` | `Item.ingest_status`; SQLite migrate |
| `src/second_read/ingest/extract.py` | `ExtractError` with title; keep `FetchError` |
| `src/second_read/ingest/__init__.py` | Stub insert on failure; `INGEST_READY` / `INGEST_PENDING_BODY` |
| `src/second_read/ingest/complete.py` | Daily complete-pending-bodies (Groq) |
| `src/second_read/config.py` | `site_url` |
| `src/second_read/bot/handlers.py` | Stub Telegram copy with Unfetched link |
| `src/second_read/rank/run.py` | Filter `ready`; call complete before rank |
| `web/lib/supabase.ts` | `ingest_status`, `extracted_text` on `ItemRow` |
| `web/app/actions.ts` | `submitArticleBody` server action |
| `web/lib/pdf.ts` | PDF → text helper |
| `web/components/ui.tsx` | Nav tab Unfetched |
| `web/components/UnfetchedCard.tsx` | Paste article expand UI |
| `web/app/unfetched/page.tsx` | List `pending_body` |
| `web/app/{unread,all,topics}/page.tsx` | Filter `ingest_status=ready` |
| `tests/test_ingest_stub.py` | Stub on fetch/extract failure |
| `tests/test_complete_pending.py` | Daily completion |
| `tests/test_persist_ranking.py` | Stubs excluded |
| `.env.example`, `README.md`, `CHANGELOG.md` | Docs |

---

### Task 1: `ingest_status` schema and model

**Files:**
- Create: `supabase/migrations/20260826000000_ingest_status.sql`
- Modify: `src/second_read/db/__init__.py`
- Test: `tests/test_ingest_status_column.py`

**Interfaces:**
- Produces: `Item.ingest_status: str` with default `"ready"`; SQLite `_migrate_sqlite` adds column if missing

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ingest_status_column.py
from second_read.db import Item, get_session, init_db


def test_new_item_defaults_ingest_status_ready(tmp_path):
    init_db(f"sqlite:///{tmp_path / 't.db'}")
    session = get_session()
    try:
        item = Item(url="https://example.com/a", title="A")
        session.add(item)
        session.commit()
        session.refresh(item)
        assert item.ingest_status == "ready"
    finally:
        session.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ingest_status_column.py::test_new_item_defaults_ingest_status_ready -v`

Expected: FAIL (`ingest_status` missing on `Item` or DB)

- [ ] **Step 3: Add migration + model**

```sql
-- supabase/migrations/20260826000000_ingest_status.sql
alter table items
  add column if not exists ingest_status varchar(32) not null default 'ready';

create index if not exists items_ingest_status_idx on items (ingest_status);
```

In `Item` (after `note` column is fine):

```python
ingest_status: Mapped[str] = mapped_column(String(32), default="ready")
```

In `_migrate_sqlite` `alters` dict:

```python
"ingest_status": "ALTER TABLE items ADD COLUMN ingest_status VARCHAR(32) DEFAULT 'ready'",
```

After adding the column in SQLite migrate, backfill nulls if needed:

```python
conn.exec_driver_sql(
    "UPDATE items SET ingest_status = 'ready' "
    "WHERE ingest_status IS NULL OR ingest_status = ''"
)
```

(Only run that UPDATE after the column exists.)

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ingest_status_column.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add supabase/migrations/20260826000000_ingest_status.sql \
  src/second_read/db/__init__.py tests/test_ingest_status_column.py
git commit -m "Add ingest_status column for incomplete corpus stubs."
```

---

### Task 2: `ExtractError` and richer extract failures

**Files:**
- Modify: `src/second_read/ingest/extract.py`
- Test: `tests/test_extract_error.py`

**Interfaces:**
- Produces: `class ExtractError(Exception)` with `.title: str` and `.status_code` unused; raised when HTML fetched but body too short
- Consumes: existing `_fetch_html`, trafilatura

- [ ] **Step 1: Write the failing test**

```python
# tests/test_extract_error.py
import pytest

from second_read.ingest.extract import ExtractError, extract_article


def test_short_html_raises_extract_error_with_title(monkeypatch):
    html = "<html><head><title>Paywalled Piece</title></head><body>Hi</body></html>"

    def fake_fetch(url: str, timeout: float) -> str:
        return html

    monkeypatch.setattr("second_read.ingest.extract._fetch_html", fake_fetch)

    with pytest.raises(ExtractError) as excinfo:
        extract_article("https://example.com/paywall")

    assert excinfo.value.title == "Paywalled Piece"
    assert "enough article text" in str(excinfo.value).lower() or "extract" in str(excinfo.value).lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_extract_error.py::test_short_html_raises_extract_error_with_title -v`

Expected: FAIL (`ExtractError` missing or still `ValueError`)

- [ ] **Step 3: Implement `ExtractError` and raise it**

In `extract.py`, after `FetchError`:

```python
class ExtractError(Exception):
    """HTML fetched but main article text could not be extracted."""

    def __init__(self, message: str, *, title: str) -> None:
        super().__init__(message)
        self.title = title
```

Replace the short-text `ValueError` with:

```python
if not extracted or len(extracted.strip()) < 80:
    raise ExtractError(
        "Could not extract enough article text from URL",
        title=title.strip() or url,
    )
```

Keep `title = (meta.title if meta and meta.title else "") or url` before that check.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_extract_error.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/second_read/ingest/extract.py tests/test_extract_error.py
git commit -m "Raise ExtractError with page title when body extraction fails."
```

---

### Task 3: Persist stub on fetch/extract failure (no Groq)

**Files:**
- Modify: `src/second_read/ingest/__init__.py`
- Test: `tests/test_ingest_stub.py`

**Interfaces:**
- Consumes: `FetchError`, `ExtractError`, `Item`, `get_session`
- Produces: constants `INGEST_READY = "ready"`, `INGEST_PENDING_BODY = "pending_body"`, `NOT_AVAILABLE = "not available"`; `ingest_url` returns stub `(Item, True)` without calling LLM on those errors

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_ingest_stub.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_ingest_stub.py -v`

Expected: FAIL (exceptions bubble / no stub)

- [ ] **Step 3: Implement stub path in `ingest_url`**

At top of `src/second_read/ingest/__init__.py`:

```python
from second_read.ingest.extract import ExtractError, FetchError, extract_article

INGEST_READY = "ready"
INGEST_PENDING_BODY = "pending_body"
NOT_AVAILABLE = "not available"


def _save_stub(
    *,
    url: str,
    title: str,
    note: str,
    note_clean: str | None,
) -> Item:
    session = get_session()
    try:
        existing = session.query(Item).filter_by(url=url).one_or_none()
        if existing:
            session.expunge(existing)
            return existing
        item = Item(
            url=url,
            title=title or url,
            snapshot=NOT_AVAILABLE,
            subject=NOT_AVAILABLE,
            topics=[],
            keywords=[],
            extracted_text="",
            priority=3,
            note=note_clean or note,
            ingest_status=INGEST_PENDING_BODY,
        )
        session.add(item)
        session.commit()
        session.refresh(item)
        session.expunge(item)
        return item
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

Wrap the extract/summarize block:

```python
    try:
        title_hint, text = extract_article(url)
    except FetchError as exc:
        item = _save_stub(url=url, title=url, note=str(exc), note_clean=note_clean)
        return item, True  # if just created; if existing returned, created=False
    except ExtractError as exc:
        item = _save_stub(url=url, title=exc.title, note=str(exc), note_clean=note_clean)
        return item, True
```

Fix created flag properly: `_save_stub` should return `tuple[Item, bool]` matching whether an insert happened (mirror existing dedup: if `existing` before insert → `False`).

On success path, set `ingest_status=INGEST_READY` on the new `Item(...)`.

Do **not** call `summarize_article` in the except branches.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ingest_stub.py tests/test_ingest_dedup.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/second_read/ingest/__init__.py tests/test_ingest_stub.py
git commit -m "Save pending_body stubs when fetch or extract fails."
```

---

### Task 4: Telegram stub message + `SITE_URL`

**Files:**
- Modify: `src/second_read/config.py`
- Modify: `src/second_read/bot/handlers.py`
- Modify: `.env.example`
- Test: `tests/test_stub_telegram_message.py` (pure helper preferred)

**Interfaces:**
- Produces: `Settings.site_url: str = ""`; `format_stub_ack(site_url: str, *, prefix: str = "") -> str`
- Consumes: `item.ingest_status == "pending_body"` after `ingest_url`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_stub_telegram_message.py
from second_read.bot.handlers import format_stub_ack


def test_format_stub_ack_includes_unfetched_link():
    text = format_stub_ack("https://readurlist.example")
    assert "could not be retrieved" in text.lower() or "could not retrieve" in text.lower()
    assert "https://readurlist.example/unfetched" in text


def test_format_stub_ack_without_site_url():
    text = format_stub_ack("")
    assert "unfetched" in text.lower()
    assert "http" not in text  # no broken link
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_stub_telegram_message.py -v`

Expected: FAIL (`format_stub_ack` missing)

- [ ] **Step 3: Implement helper, settings, handler branch**

`config.py`:

```python
site_url: str = ""
```

`.env.example`:

```
# Public website origin for Telegram links (no trailing slash)
SITE_URL=https://your-app.vercel.app
```

In `handlers.py`:

```python
def format_stub_ack(site_url: str, *, prefix: str = "") -> str:
    base = (site_url or "").rstrip("/")
    if base:
        link = f"{base}/unfetched"
        body = (
            "Saved, but the article could not be retrieved. "
            f"Paste the text or a PDF on the Unfetched page: {link}"
        )
    else:
        body = (
            "Saved, but the article could not be retrieved. "
            "Paste the text or a PDF on the website Unfetched page."
        )
    return f"{prefix}{body}"
```

In the URL loop after `ingest_url`:

```python
            item, created = await asyncio.to_thread(ingest_url, url, llm, settings)
            if item.ingest_status == "pending_body":
                await update.message.reply_text(
                    format_stub_ack(settings.site_url, prefix=prefix)
                )
                continue
```

Remove the `except FetchError` branch that only replies with the error **or** keep it only for unexpected cases — after Task 3, `FetchError`/`ExtractError` should not escape `ingest_url`. Leave a generic `except Exception` for true failures. Delete or stop catching `FetchError` specifically if stubs absorb them.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_stub_telegram_message.py tests/test_ingest_stub.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/second_read/config.py src/second_read/bot/handlers.py \
  .env.example tests/test_stub_telegram_message.py
git commit -m "Point Telegram stub saves at the Unfetched page via SITE_URL."
```

---

### Task 5: Exclude `pending_body` from ranking

**Files:**
- Modify: `src/second_read/rank/run.py` (`persist_ranking`)
- Modify: `tests/test_persist_ranking.py` (add case) or create `tests/test_ranking_skips_stubs.py`

**Interfaces:**
- Consumes: `Item.ingest_status`
- Produces: ranking/clusters only over `ingest_status == "ready"` (treat missing/empty as ready for safety: `!= "pending_body"`)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ranking_skips_stubs.py
from datetime import datetime, timezone

from second_read.db import DailyPick, Item, get_session, init_db
from second_read.rank.run import persist_ranking


def test_pending_body_stub_not_in_daily_picks(tmp_path):
    init_db(f"sqlite:///{tmp_path / 't.db'}")
    now = datetime(2026, 8, 26, 8, 0, tzinfo=timezone.utc)
    session = get_session()
    try:
        session.add_all(
            [
                Item(
                    url="https://example.com/ready",
                    title="Ready",
                    snapshot="a real snapshot about trees",
                    subject="climate",
                    topics=["climate"],
                    keywords=["trees"],
                    extracted_text="x" * 80,
                    priority=4,
                    ingest_status="ready",
                    created_at=now,
                ),
                Item(
                    url="https://example.com/stub",
                    title="https://example.com/stub",
                    snapshot="not available",
                    subject="not available",
                    topics=[],
                    keywords=[],
                    extracted_text="",
                    priority=3,
                    ingest_status="pending_body",
                    created_at=now,
                ),
            ]
        )
        session.commit()
    finally:
        session.close()

    picks = persist_ranking(now=now)
    ids = {p.item_id for p in picks}
    session = get_session()
    try:
        stub = session.query(Item).filter_by(url="https://example.com/stub").one()
        ready = session.query(Item).filter_by(url="https://example.com/ready").one()
        assert stub.id not in ids
        assert ready.id in ids or session.query(DailyPick).filter_by(item_id=ready.id).count() == 1
    finally:
        session.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ranking_skips_stubs.py -v`

Expected: FAIL (stub included or pollutes picks)

- [ ] **Step 3: Filter in `persist_ranking`**

Change:

```python
items = session.query(Item).all()
```

to:

```python
items = (
    session.query(Item)
    .filter(Item.ingest_status != "pending_body")
    .all()
)
```

(If SQLite has old rows without the column, Task 1 migration already defaulted them.)

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_ranking_skips_stubs.py tests/test_persist_ranking.py tests/test_rank.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/second_read/rank/run.py tests/test_ranking_skips_stubs.py
git commit -m "Exclude pending_body stubs from ranking and clusters."
```

---

### Task 6: Daily complete-pending-bodies (before digest)

**Files:**
- Create: `src/second_read/ingest/complete.py`
- Modify: `src/second_read/rank/run.py` (`run_digest_job`)
- Modify: `src/second_read/bot/handlers.py` (`handle_digest` already calls `run_digest_job`)
- Modify: `src/second_read/rank/__main__.py` path via `run_digest_job` / CLI
- Test: `tests/test_complete_pending.py`

**Interfaces:**
- Produces: `async def complete_pending_bodies(bot, llm, settings) -> int` — number completed; sync helper `complete_pending_bodies_sync(llm, settings) -> list[Item]` for tests
- Consumes: `summarize_article`, items with `pending_body` and non-empty `extracted_text`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_complete_pending.py
from second_read.config import Settings
from second_read.db import Item, get_session, init_db
from second_read.ingest.complete import complete_pending_bodies_sync
from second_read.ingest.summarize import IngestResult
from second_read.llm.base import LLMProvider


class FakeLLM:
    def complete(self, prompt, *, model, system=None, schema=None, temperature=0.3) -> str:
        return (
            '{"title": "Filled", "snapshot": "Now we have a snapshot.",'
            ' "subject": "testing", "topics": ["tests"], "keywords": ["pytest"],'
            ' "priority": 4}'
        )


def test_complete_pending_fills_ready_item(tmp_path, monkeypatch):
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_complete_pending.py -v`

Expected: FAIL (module missing)

- [ ] **Step 3: Implement completion**

```python
# src/second_read/ingest/complete.py
from __future__ import annotations

import logging

from telegram import Bot

from second_read.config import Settings
from second_read.db import Item, get_session
from second_read.ingest import INGEST_PENDING_BODY, INGEST_READY
from second_read.ingest.summarize import summarize_article
from second_read.llm.base import LLMProvider

logger = logging.getLogger(__name__)


def complete_pending_bodies_sync(llm: LLMProvider, settings: Settings) -> list[Item]:
    session = get_session()
    completed: list[Item] = []
    try:
        rows = (
            session.query(Item)
            .filter(Item.ingest_status == INGEST_PENDING_BODY)
            .all()
        )
        for row in rows:
            body = (row.extracted_text or "").strip()
            if not body:
                continue
            try:
                result = summarize_article(
                    llm,
                    model=settings.model_ingest,
                    url=row.url,
                    title_hint=row.title or row.url,
                    text=body,
                )
            except Exception as exc:
                logger.exception("Complete pending failed for item %s", row.id)
                row.note = f"complete failed: {exc}"[:500]
                session.commit()
                continue
            row.title = result.title
            row.snapshot = result.snapshot
            row.subject = result.subject
            row.topics = list(result.topics)
            row.keywords = list(result.keywords)
            row.priority = result.priority
            row.ingest_status = INGEST_READY
            session.commit()
            session.refresh(row)
            session.expunge(row)
            completed.append(row)
        return completed
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def complete_pending_bodies(
    bot: Bot,
    llm: LLMProvider,
    settings: Settings,
) -> int:
    done = complete_pending_bodies_sync(llm, settings)
    for item in done:
        title = item.title or item.url
        await bot.send_message(
            chat_id=settings.telegram_user_id,
            text=f"Filled in {title} from your paste/PDF.",
            disable_web_page_preview=True,
        )
    return len(done)
```

Wire into `run_digest_job` — needs `llm` on the job. Today `run_digest_job(bot, settings)` has no llm. Change signature:

```python
async def run_digest_job(
    bot: Bot,
    settings: Settings,
    llm: LLMProvider | None = None,
    *,
    force: bool = False,
) -> bool:
```

At start:

```python
    if llm is not None:
        await complete_pending_bodies(bot, llm, settings)
```

Update callers:

- `handle_digest`: pass `context.application.bot_data["llm"]`
- `_scheduled_digest`: pass `context.application.bot_data["llm"]`
- CLI `main()` in `rank/run.py`: construct `GroqProvider` like `main.py` and pass it

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_complete_pending.py tests/test_digest_idempotency.py -v`

Expected: PASS (fix digest callers if signature broke tests — update mocks)

- [ ] **Step 5: Commit**

```bash
git add src/second_read/ingest/complete.py src/second_read/rank/run.py \
  src/second_read/bot/handlers.py src/second_read/bot/__init__.py \
  tests/test_complete_pending.py
git commit -m "Complete pending_body items with Groq before daily digest."
```

---

### Task 7: Website — types, hide stubs, Unfetched page + paste text

**Files:**
- Modify: `web/lib/supabase.ts`
- Modify: `web/components/ui.tsx` (Nav)
- Modify: `web/app/unread/page.tsx`, `web/app/all/page.tsx`, `web/app/topics/page.tsx`
- Create: `web/app/unfetched/page.tsx`
- Create: `web/components/UnfetchedCard.tsx`
- Modify: `web/app/actions.ts`
- Modify: `web/app/globals.css` (minimal styles for expand form if needed)

**Interfaces:**
- Produces: `submitArticleBody(itemId, formData)` server action; `/unfetched` lists `ingest_status=eq.pending_body`
- Consumes: Supabase `items.extracted_text`, `ingest_status`

- [ ] **Step 1: Extend `ItemRow` and filter corpus pages**

```typescript
// web/lib/supabase.ts — extend ItemRow
export type ItemRow = {
  id: number;
  url: string;
  title: string;
  snapshot: string;
  subject: string;
  topics: string[] | null;
  keywords: string[] | null;
  created_at: string;
  read_at: string | null;
  similar_to_item_id: number | null;
  ingest_status?: string;
  extracted_text?: string | null;
};
```

On unread / all / topics queries, add:

```typescript
.eq("ingest_status", "ready")
```

Include `ingest_status` in selects where useful. Clusters are built from ranking members already filtered on the NUC after Task 5; no change strictly required, but filtering member items client-side `item.ingest_status !== "pending_body"` is harmless.

Add Nav entry in `ui.tsx`:

```typescript
["/unfetched", "Unfetched"],
```

- [ ] **Step 2: Server action for text body**

```typescript
// web/app/actions.ts — add
export async function submitArticleBody(itemId: number, formData: FormData) {
  const db = supabaseAdmin();
  const text = String(formData.get("body") || "").trim();
  const file = formData.get("pdf");
  let body = text;
  if (!body && file && typeof file === "object" && "arrayBuffer" in file) {
    const { extractPdfText } = await import("@/lib/pdf");
    body = (await extractPdfText(file as File)).trim();
  }
  if (!body) {
    throw new Error("Paste article text or upload a PDF with extractable text.");
  }
  const { data: row, error: readErr } = await db
    .from("items")
    .select("id, ingest_status")
    .eq("id", itemId)
    .maybeSingle();
  if (readErr) throw new Error(readErr.message);
  if (!row || row.ingest_status !== "pending_body") {
    throw new Error("Item is not awaiting a body.");
  }
  const { error } = await db
    .from("items")
    .update({ extracted_text: body })
    .eq("id", itemId)
    .eq("ingest_status", "pending_body");
  if (error) throw new Error(error.message);
  revalidatePath("/unfetched");
}
```

For Task 7 only, PDF branch can throw `"PDF support next"` **or** implement Task 8's `extractPdfText` stub that throws until Task 8 — prefer implementing text-only path first and wire PDF in Task 8 without leaving a dead branch: Task 7 form has textarea only; Task 8 adds PDF input + `lib/pdf.ts`.

Task 7 action:

```typescript
export async function submitArticleBody(itemId: number, formData: FormData) {
  const db = supabaseAdmin();
  const body = String(formData.get("body") || "").trim();
  if (!body) {
    throw new Error("Paste article text.");
  }
  // ... same guards and update ...
}
```

- [ ] **Step 3: `UnfetchedCard` + page**

```tsx
// web/components/UnfetchedCard.tsx
"use client";

import { useState } from "react";
import { submitArticleBody } from "@/app/actions";
import type { ItemRow } from "@/lib/supabase";

export function UnfetchedCard({ item }: { item: ItemRow }) {
  const [open, setOpen] = useState(false);
  const hasBody = Boolean((item.extracted_text || "").trim());
  const action = submitArticleBody.bind(null, item.id);

  return (
    <article className="item">
      <a className="item-title" href={item.url} target="_blank" rel="noopener noreferrer">
        {item.title || item.url}
      </a>
      {item.note ? <p className="item-note">{item.note}</p> : null}
      {hasBody ? (
        <p className="item-reason">Queued for today’s fill-in</p>
      ) : (
        <p className="item-reason">Needs article text</p>
      )}
      <button type="button" className="ghost" onClick={() => setOpen((v) => !v)}>
        Paste article
      </button>
      {open ? (
        <form action={action} className="paste-form">
          <textarea name="body" rows={8} placeholder="Paste article text…" defaultValue="" />
          <button type="submit">Save for fill-in</button>
        </form>
      ) : null}
    </article>
  );
}
```

```tsx
// web/app/unfetched/page.tsx
import { Shell } from "@/components/ui";
import { UnfetchedCard } from "@/components/UnfetchedCard";
import { supabaseAdmin, type ItemRow } from "@/lib/supabase";

export const dynamic = "force-dynamic";

export default async function UnfetchedPage() {
  const db = supabaseAdmin();
  const { data, error } = await db
    .from("items")
    .select(
      "id, url, title, snapshot, subject, topics, keywords, created_at, read_at, similar_to_item_id, ingest_status, extracted_text, note",
    )
    .eq("ingest_status", "pending_body")
    .order("created_at", { ascending: false });
  if (error) throw new Error(error.message);
  const items = (data || []) as ItemRow[];
  return (
    <Shell current="/unfetched">
      <h2 className="section-title">Unfetched</h2>
      {items.length === 0 ? (
        <p className="empty">No items waiting for article text.</p>
      ) : (
        items.map((item) => <UnfetchedCard key={item.id} item={item} />)
      )}
    </Shell>
  );
}
```

Add `note?: string | null` to `ItemRow` if used.

Minimal CSS in `globals.css`:

```css
.paste-form {
  display: grid;
  gap: 0.75rem;
  margin-top: 0.75rem;
}
.paste-form textarea {
  width: 100%;
  font: inherit;
}
```

- [ ] **Step 4: Manual check**

Run: `cd web && npm run build`

Expected: build succeeds

- [ ] **Step 5: Commit**

```bash
git add web/lib/supabase.ts web/components/ui.tsx web/components/UnfetchedCard.tsx \
  web/app/unfetched/page.tsx web/app/actions.ts web/app/globals.css \
  web/app/unread/page.tsx web/app/all/page.tsx web/app/topics/page.tsx
git commit -m "Add Unfetched page and paste-text fill-in for stubs."
```

---

### Task 8: PDF upload on Unfetched

**Files:**
- Create: `web/lib/pdf.ts`
- Modify: `web/components/UnfetchedCard.tsx`
- Modify: `web/app/actions.ts`
- Modify: `web/package.json` (add `unpdf`)

**Interfaces:**
- Produces: `extractPdfText(file: File): Promise<string>`
- Consumes: `submitArticleBody` accepts `pdf` file field

- [ ] **Step 1: Install dependency**

Run: `cd web && npm install unpdf`

- [ ] **Step 2: Implement PDF helper**

```typescript
// web/lib/pdf.ts
import { extractText, getDocumentProxy } from "unpdf";

export async function extractPdfText(file: File): Promise<string> {
  const buffer = new Uint8Array(await file.arrayBuffer());
  const pdf = await getDocumentProxy(buffer);
  const { text } = await extractText(pdf, { mergePages: true });
  return (text || "").trim();
}
```

- [ ] **Step 3: Wire form + action**

In `UnfetchedCard` form:

```tsx
<input type="file" name="pdf" accept="application/pdf" />
```

In `submitArticleBody`:

```typescript
  let body = String(formData.get("body") || "").trim();
  const pdf = formData.get("pdf");
  if (!body && pdf instanceof File && pdf.size > 0) {
    const { extractPdfText } = await import("@/lib/pdf");
    body = (await extractPdfText(pdf)).trim();
  }
  if (!body) {
    throw new Error("Paste article text or upload a PDF with extractable text.");
  }
```

- [ ] **Step 4: Build**

Run: `cd web && npm run build`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/package.json web/package-lock.json web/lib/pdf.ts \
  web/components/UnfetchedCard.tsx web/app/actions.ts
git commit -m "Allow PDF upload on Unfetched to supply article text."
```

---

### Task 9: Docs and changelog

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `.env.example` (if not done in Task 4)
- Modify: `web/.env.example` only if needed (no new web secrets)

- [ ] **Step 1: Update README**

Document:

- Fetch failures save a stub; fill in on Unfetched
- `SITE_URL` for Telegram links
- Apply migration `20260826000000_ingest_status.sql`
- Daily digest completes pending bodies then ranks

- [ ] **Step 2: Update CHANGELOG `[Unreleased]`**

```markdown
### Added
- Fetch/extract failures save `pending_body` stubs; Unfetched page for paste/PDF; daily NUC Groq fill-in before digest.
```

- [ ] **Step 3: Run full pytest**

Run: `pytest -q`

Expected: all PASS

- [ ] **Step 4: Commit**

```bash
git add README.md CHANGELOG.md .env.example
git commit -m "Document fetch-failure stubs and Unfetched fill-in."
```

---

## Spec coverage self-review

| Spec requirement | Task |
|------------------|------|
| `ingest_status` ready / pending_body | 1 |
| Stub fields (`not available`, empty tags, note) | 3 |
| FetchError + ExtractError → stub, keep title | 2, 3 |
| No Groq on stub path | 3 |
| Telegram Unfetched link + SITE_URL | 4 |
| Dedup unchanged | 3 |
| Ranking/digest exclude stubs | 5 |
| Daily complete before digest / `/digest` | 6 |
| `/unfetched` + Paste article | 7 |
| Textarea + PDF | 7, 8 |
| Hide stubs from corpus views | 7 |
| Groq NUC only | 6, 7, 8 |
| Docs | 9 |

## Placeholder scan

No TBD/TODO left in task steps. PDF uses `unpdf` explicitly. `run_digest_job` LLM wiring called out.

## Type consistency

- Status strings: `"ready"` / `"pending_body"` via `INGEST_READY` / `INGEST_PENDING_BODY`
- `complete_pending_bodies_sync(llm, settings) -> list[Item]`
- `format_stub_ack(site_url, *, prefix="") -> str`
- Website filter: `.eq("ingest_status", "ready")`
