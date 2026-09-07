# ReadURList

Paste URLs in Telegram, get an AI snapshot, store them in Postgres, and receive a daily ranked “read these” list. Skip what you are not reading now. A password-gated website reorganizes the backlog.

Single-user by design: the bot allowlists one Telegram account; the site is gated by a shared password.

See [context.md](context.md) for product principles and [CHANGELOG.md](CHANGELOG.md) for history.

## What you need

- Python 3.11+
- A machine that can stay running (the **worker** polls Telegram and runs Groq)
- A Telegram bot token ([@BotFather](https://t.me/BotFather)) and your numeric user id (see [Telegram bot setup](#telegram-bot-setup))
- A [Groq](https://console.groq.com) API key
- A [Supabase](https://supabase.com) project (Postgres)
- A [Vercel](https://vercel.com) project for the website (optional until you want the UI off the worker host)

Article text is sent to Groq and stored in Supabase. Do not save secrets into the corpus.

## Telegram bot setup

The worker talks to Telegram with **long polling** (`getUpdates`). There is no webhook. Only the allowlisted user id can capture URLs or press digest buttons; everyone else is ignored.

### 1. Create the bot

1. Open Telegram and message **[@BotFather](https://t.me/BotFather)** (verified badge). Impostor accounts exist; do not paste a token into the wrong chat.
2. Send `/newbot`.
3. Choose a **display name** (shown in the chat header; you can change this later with `/setname`).
4. Choose a **username**. It must be unique, 5–32 characters, and end in `bot` (for example `readurlist_bot`). Usernames cannot be changed.
5. BotFather replies with an **API token** that looks like `123456789:AAH…`. Treat it like a password. Anyone with it can send and receive as this bot.

If the token leaks, send `/revoke` in BotFather, then put the new value in `.env`. `/token` only shows the current key. The bot identity stays; only the key changes.

### 2. Optional BotFather settings

Still in BotFather:

- `/setdescription` — short “What can this bot do?” text before `/start`.
- `/setabouttext` — profile bio (≤120 characters).
- `/setuserpic` — profile photo.
- `/setcommands` — the `/` menu. Paste:

  ```
  start - Confirm the bot is listening
  digest - Rank unread items now (Telegram digest at most once per day)
  ```

- `/setjoingroups` → **Disable**. This bot is a private DM capture surface, not a group bot.
- `/setprivacy` — leave the default. It only matters in groups.

Do **not** set a webhook (BotFather has no webhook command; other tools or `setWebhook` can). Polling and webhooks are mutually exclusive. If a webhook is already set, long polling stays silent until you clear it:

```bash
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/deleteWebhook"
```

### 3. Get your numeric user id

`TELEGRAM_USER_ID` must be the integer Telegram assigns to **your** account, not the bot, and not your `@username`.

Easiest: message [**@userinfobot**](https://t.me/userinfobot) (or [@RawDataBot](https://t.me/RawDataBot)) and copy the `Id` number.

Or, after the worker has run once and you have sent the bot any message:

```bash
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getUpdates"
```

Look for `"from": { "id": … }` on your message. That value is `TELEGRAM_USER_ID`. The daily digest also uses it as the chat id, so you must `/start` the bot at least once before it can message you.

### 4. Put it in `.env`

```
TELEGRAM_BOT_TOKEN=123456789:AAH…
TELEGRAM_USER_ID=123456789
```

Then start the worker (`readurlist`). Open the bot in Telegram and send `/start`. You should get the listening message. Paste a URL next.

Only one process may poll a given token. A second `readurlist` (or any other client) produces HTTP 409 and a silent bot.

### Using the bot

| You send | What happens |
| --- | --- |
| One or more `http(s)` URLs | Sequential `n/N` snapshots. Fetch/extract failure → stub + Unfetched link. |
| `/start` | Confirms the allowlisted user and lists capture / digest / website. |
| `/digest` | Completes pasted Unfetched bodies, consolidates tags if needed, ranks, and sends today's digest **only if it has not already been sent today**. |
| Daily at `DIGEST_HOUR` | Same ranking job, unforced. Digest at most once per day. |
| **Mark read · n** / **Skip · n** on a digest | Marks that pick read, or skips it (leaves the queue without marking read). |

Plain text with no URL gets a short usage hint. Non-allowlisted users get no reply.

If Telegram is silent: is the worker process running, is exactly one `readurlist` polling this token, is the token current, and did you `/start` from the account whose id is in `.env`?

## Worker

The worker must stay up: it polls Telegram, calls Groq, and sends the daily digest. Run it on any always-on host.

```bash
cd ReadURList
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# edit .env
```

Set `DATABASE_URL` to the Supabase **session pooler** (port 5432) using the SQLAlchemy driver. Direct `db.PROJECT.supabase.co` hosts are often IPv6-only; the pooler hostname from **Project Settings → Database** is the one that works from a typical machine.

```
DATABASE_URL=postgresql+psycopg://postgres.PROJECT:PASSWORD@HOST:5432/postgres?sslmode=require
```

Apply every file in [`supabase/migrations/`](supabase/migrations/) in timestamp order (SQL editor or `supabase db push`). Later migrations add `ingest_status` (fetch-failure stubs), drop clusters, and add `skipped_at` (leave the ranking queue without marking read).

```bash
readurlist
```

Set `SITE_URL` to the public website origin (no trailing slash). Telegram uses it for Unfetched links when a URL could not be retrieved.

Before ranking, the daily job (and `/digest`) runs Groq ingest on stubs that already have pasted text, then consolidates near-duplicate subjects/topics when the vocabulary has fragmented. It ranks only **ready** items that are neither read nor skipped: subject demand 0.45, recency 0.20, path novelty 0.20, LLM priority 0.15; at most two picks per subject, top 5. Keywords stay on cards as display. Ranking reasons are templates, not an extra LLM call.

### Start on boot (macOS)

Copy [`docs/com.readurlist.worker.plist`](docs/com.readurlist.worker.plist), replace `/PATH/TO/ReadURList` with the clone path, then:

```bash
cp docs/com.readurlist.worker.plist ~/Library/LaunchAgents/com.readurlist.worker.plist
launchctl load ~/Library/LaunchAgents/com.readurlist.worker.plist
```

Linux: a systemd user unit with `ExecStart=…/.venv/bin/readurlist` and `Restart=always`.

### Start on boot (Windows)

After `readurlist` works in a console, use Task Scheduler with **Run only when user is logged on** (no account password) and hide the window:

1. Action → Start a program  
   - Program: `wscript.exe`  
   - Arguments: `"C:\PATH\TO\ReadURList\docs\run-worker-hidden.vbs"`  
   - Start in: `C:\PATH\TO\ReadURList`
2. Trigger: **At log on** (pair with Windows auto-login if the host reboots unattended).
3. Settings: restart on failure every 1 minute, up to 3 times.

See [`docs/run-worker-hidden.vbs`](docs/run-worker-hidden.vbs).

### Manual digest / ranking

```bash
readurlist-digest
```

Or `/digest` in Telegram.

### Migrate an old local SQLite file

```bash
python scripts/migrate_sqlite.py ./data/old.sqlite
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

Point `web/.env.local` at a database you are willing to mutate. Mark read and skip write to that database. **Send to Unfetched** clears article text and queues fill-in — do not use it against production data from localhost.

Three tabs: **Today** (ranked picks plus a short ranking explainer; sidebar is that day’s subjects/tags), **All** (library), **Unfetched** (stubs). Light/dark theme. `/unread` and `/topics` redirect into All.

**All:** filters All / Unread / Stale 14+ / Read / Skipped. Unread is the ranking queue (ready, not skipped). Cards can mark read, skip, or restore. Edit can overwrite headline, description, subject, and topics, or **Send to Unfetched** after confirm. **Organize** (button on All, not a tab) merges singleton labels, batch-edits subject/topics, and lists the oldest unread items.

**Unfetched:** lists items the worker could not retrieve. Open **Paste article**, paste text or upload a PDF (max 3.5 MB — Vercel serverless limit). Saved text is ingested on the worker at the next daily digest (or when you run `/digest` / `readurlist-digest`). Stubs are hidden from Today and All until ingest completes.

## Backup

The corpus is in Supabase. Turn on backups in the project, or periodically dump with `supabase db dump` / `pg_dump`.

A local SQLite file is not a backup once capture writes to Postgres.

## Models

Change Groq model: set `MODEL_INGEST` in `.env` and restart. Default is `openai/gpt-oss-120b` (Groq retired `llama-3.3-70b-versatile` for free/developer on 16 Aug 2026). Ingest is given the current subject/topic lists and prefers existing labels. Groq JSON uses structured outputs; prompts are truncated to stay under on-demand TPM.

## Tests

```bash
source .venv/bin/activate
pytest -q
```

CI runs pytest on push. Website builds on Vercel.

Do not commit `.env`, `web/.env.local`, `web/node_modules`, `web/.next`, or `web/tsconfig.tsbuildinfo` (already gitignored).

## Stack

Python · `python-telegram-bot` · SQLAlchemy · Groq · trafilatura · Supabase Postgres · Next.js on Vercel
