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

Apply [`supabase/migrations/20260820000000_init_corpus.sql`](supabase/migrations/20260820000000_init_corpus.sql) in the Supabase SQL editor (or `supabase db push` if you use the CLI).

```bash
second-read
```

Telegram: `/start`, then paste one or more URLs. Snapshot comes back per URL. `/digest` runs ranking now (sends the Telegram digest at most once per day). Daily digest is scheduled at `DIGEST_HOUR` (default 08:00, NUC local time).

If Telegram is silent: is the NUC up, and is `second-read` running?

### Start on boot (macOS)

Copy [`docs/com.readurlist.worker.plist`](docs/com.readurlist.worker.plist), replace `YOU` with your paths, then:

```bash
cp docs/com.readurlist.worker.plist ~/Library/LaunchAgents/com.readurlist.worker.plist
launchctl load ~/Library/LaunchAgents/com.readurlist.worker.plist
```

Linux: a systemd user unit with `ExecStart=…/.venv/bin/second-read` and `Restart=always`.

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

Views: Today (ranked picks + reading path), Unread (optional stale 14+ days), Topics, Clusters, All. Mark read/unread on every card.

## Backup

The corpus is in Supabase. Turn on backups in the project, or periodically:

```bash
# from psql / supabase db dump
```

A local SQLite file is not a backup once capture writes to the cloud.

## Models

Change Groq model: set `MODEL_INGEST` in `.env` and restart. No code change. Ranking reasons are templates, not an extra LLM call.

## Tests

```bash
source .venv/bin/activate
pytest -q
```

CI runs pytest on push. Website builds on Vercel.

## Stack

Python · `python-telegram-bot` · SQLAlchemy · Groq · trafilatura · Supabase Postgres · Next.js on Vercel
