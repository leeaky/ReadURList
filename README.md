# ReadURList

Personal reading corpus: paste URLs in Telegram, get an AI snapshot, store them in the cloud, and get a daily ranked “read these” list. A password-gated website reorganizes the backlog.

See [context.md](context.md) for product principles and [CHANGELOG.md](CHANGELOG.md) for history.

## What you need

- Python 3.11+
- A Telegram bot token ([@BotFather](https://t.me/BotFather)) and your user id ([@userinfobot](https://t.me/userinfobot))
- A [Groq](https://console.groq.com) API key
- A [Supabase](https://supabase.com) project (Postgres)
- A [Vercel](https://vercel.com) project for the website (optional until you want the UI off-NUC)

Article text is sent to Groq and stored in Supabase. Fine for personal use; do not save secrets.

## Worker (NUC)

```bash
cd ReadURList
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# edit .env
```

Set `DATABASE_URL` to the Supabase **session pooler** (port 5432) using the SQLAlchemy driver. The `db.PROJECT.supabase.co` host has no public A record on this project.

```
DATABASE_URL=postgresql+psycopg://postgres.PROJECT:PASSWORD@aws-0-ap-southeast-2.pooler.supabase.com:5432/postgres?sslmode=require
```

Apply migrations in the Supabase SQL editor (or `supabase db push` if you use the CLI):

- [`supabase/migrations/20260820000000_init_corpus.sql`](supabase/migrations/20260820000000_init_corpus.sql)
- [`supabase/migrations/20260826000000_ingest_status.sql`](supabase/migrations/20260826000000_ingest_status.sql) — adds `ingest_status` (`ready` / `pending_body`) for fetch-failure stubs
- [`supabase/migrations/20260904000000_skipped_at.sql`](supabase/migrations/20260904000000_skipped_at.sql) — adds `skipped_at` so items can leave the ranking queue without being marked read

```bash
second-read
```

Set `SITE_URL` to your public Vercel origin (no trailing slash). Telegram uses it for links to the Unfetched page when a URL could not be retrieved.

Telegram: `/start`, then paste one or more URLs. Snapshot comes back per URL. If fetch or extract fails, the item is saved as a stub (`ingest_status=pending_body`) with the title when available; the bot replies with a link to fill in the body on the website. `/digest` runs ranking now (sends the Telegram digest at most once per day). Daily digest is scheduled at `DIGEST_HOUR` (default 08:00, NUC local time). Before ranking, the daily job runs Groq ingest on any stubs that already have pasted text, then ranks only `ready` items that are not skipped.

If Telegram is silent: is the NUC up, and is `second-read` running?

### Start on boot (macOS)

Copy [`docs/com.readurlist.worker.plist`](docs/com.readurlist.worker.plist), replace `YOU` with your paths, then:

```bash
cp docs/com.readurlist.worker.plist ~/Library/LaunchAgents/com.readurlist.worker.plist
launchctl load ~/Library/LaunchAgents/com.readurlist.worker.plist
```

Linux: a systemd user unit with `ExecStart=…/.venv/bin/second-read` and `Restart=always`.

### Start on boot (Windows)

After `second-read` works in a console, use Task Scheduler with **Run only when user is logged on** (no account password) and hide the window:

1. Action → Start a program  
   - Program: `wscript.exe`  
   - Arguments: `"C:\Users\YOU\dev\ReadURList\docs\run-worker-hidden.vbs"`  
   - Start in: `C:\Users\YOU\dev\ReadURList`
2. Trigger: **At log on** (pair with Windows auto-login if the NUC reboots unattended).
3. Settings: restart on failure every 1 minute, up to 3 times.

See [`docs/run-worker-hidden.vbs`](docs/run-worker-hidden.vbs).

### Manual digest / ranking

```bash
second-read-digest
```

Or `/digest` in Telegram.

### Migrate an old local SQLite file

```bash
python scripts/migrate_sqlite.py ./data/second_read.db
```

`DATABASE_URL` must already point at Postgres.

## Website (Vercel)

App lives in [`web/`](web/). In Vercel: **Root Directory** = `web`. Env:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY` (server only — never `NEXT_PUBLIC_`)
- `SITE_PASSWORD`

Local:

```bash
cd web
cp .env.example .env.local
npm install
npm run dev
```

`web/.env.local` usually points at the **same Supabase project as production**. Mark read is fine. Do not use **Send to Unfetched** (or other destructive UI) from localhost against that database — it clears article text and fill-in for real items.

Views: Today (ranked picks), All (library: Unread / Stale 14+ / Read / Skipped), **Unfetched** (stubs awaiting article text), Organize. Mark read, skip, or restore on cards.

**Unfetched:** lists items the worker could not retrieve. Open **Paste article**, paste text or upload a PDF (max 3.5 MB — Vercel serverless limit). Saved text is ingested on the NUC at the next daily digest (or when you run `/digest` / `second-read-digest`). Stubs are hidden from Today and All until ingest completes.

## Backup

The corpus is in Supabase. Turn on backups in the project, or periodically:

```bash
# from psql / supabase db dump
```

A local SQLite file is not a backup once capture writes to the cloud.

## Models

Change Groq model: set `MODEL_INGEST` in `.env` and restart. Default is `openai/gpt-oss-120b` (Groq retired `llama-3.3-70b-versatile` for free/developer on 16 Aug 2026). Ranking reasons stay templates, not an extra LLM call; ingest is given the current subject/topic lists.

## Git

One feature branch per issue (`cursor/…` is fine). Merge to `main`, then delete the branch locally and on GitHub (`git push origin --delete <branch>`). `git fetch --prune` so stale `origin/…` names disappear.

Do not commit `.env`, `web/.env.local`, `web/node_modules`, `web/.next`, or `web/tsconfig.tsbuildinfo` (already gitignored).

## Tests

```bash
source .venv/bin/activate
pytest -q
```

CI runs pytest on push. Website builds on Vercel.

## Stack

Python · `python-telegram-bot` · SQLAlchemy · Groq · trafilatura · Supabase Postgres · Next.js on Vercel
