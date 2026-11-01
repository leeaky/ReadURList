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
| Daily at `DIGEST_HOUR` | Same ranking job, unforced. Digest at most once per day. On Mondays it ends with a "Last week" line: picks read of picks shown, the verdict, skipped, and the unread pile then → now. |
| **Mark read · n** / **Skip · n** on an older digest | Marks that pick read, or skips it (leaves the queue without marking read). The daily list no longer has buttons — mark read or skip on the website's Today page. |

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

Before ranking, the daily job (and `/digest`) runs Groq ingest on stubs that already have pasted text, then consolidates near-duplicate subjects/topics when the vocabulary has fragmented. It ranks only **ready** items that are neither read nor skipped: two parts out of 100: **subject** up to 65 (65 × the item's subject's unread count ÷ the biggest subject's) and **recency** up to 35 (35 ÷ (1 + days since saved, or since restored if later)); the day's list is **3 short + 1 long** (by reading time), at most two per subject across both. When no long read is ready, the list says how many papers wait on Unfetched. Links on the previous list that aren't on today's are kept with their cause (read, skipped, outscored by newer saves, subject already has two picks) and points before and after. Each pick's reason names its bigger part and shows the points, and each day's picks are kept with both parts. Keywords stay on cards as display. Ranking reasons are templates, not an extra LLM call.

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

### Effort label

Each ready item stores its `word_count`; reading time is that at 230 words a minute, and **short** means under 15 minutes (about 3,450 words), **long** 15 or more. Items saved before this existed get it once with:

```bash
readurlist-effort-backfill
```

It only fills items still missing a count, so running it again is harmless.

**arXiv papers:** for an arXiv link (abs, pdf or html), the title and summary come from the abstract page, but the word count comes from the full paper's PDF, so papers show their real reading time. If the PDF can't be fetched, the abstract's count is kept. Papers saved before this change get their count once with:

```bash
readurlist-arxiv-lengths
```

It pauses 3 seconds between papers, as arXiv asks.

### Migrate an old local SQLite file

```bash
python scripts/migrate_sqlite.py ./data/old.sqlite
```

`DATABASE_URL` must already point at Postgres.

### Dev and live

Two copies, kept apart. Agents work only in dev; only the owner changes live.

| | Live | Dev |
|---|---|---|
| Folder | `C:\apps\ReadURList`, on `main`, run by the "ReadURList Worker" task | `C:\dev\ReadURList`, any branch |
| Telegram bot | the real bot | a second bot (picture: [`docs/dev-bot-logo.png`](docs/dev-bot-logo.png)) |
| Database | the Supabase project | local Supabase in Docker on this PC |
| Groq key | live key | a separate dev key |
| Website | Vercel production, built only from `main` | `npm run dev` in `web/`, at `http://localhost:3000` |

Vercel previews get no database keys (the live ones are set for Production only, and the dev database isn't reachable from Vercel), so previews show no data. Check website changes locally.

**Dev database.** Start Docker Desktop, then from `C:\dev\ReadURList`:

```bash
npx supabase@2.122.0 start
```

It applies every file in `supabase/migrations/`. `npx supabase@2.122.0 db reset --local` wipes it and reloads the made-up sample items in [`supabase/seed.sql`](supabase/seed.sql). `npx supabase@2.122.0 status -o env` prints the local values for `.env` (`DATABASE_URL`, with `postgresql+psycopg://`) and `web/.env.local` (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`). `npx supabase@2.122.0 stop` shuts it down. Never copy live data into dev.

**Deploy order** (owner only), for a change that touches the database:

Steps 1–2 in one go, from either folder, with Docker running:

```powershell
.\scripts\live-db-deploy.ps1 20261101000000_word_count.sql
```

It asks for the live session-pooler address (not shown, never saved), writes a schema and a data backup to `C:\backups`, stops if either is empty, then applies the named migration file(s) in order and stops at the first error. Restoring the data backup needs `--disable-triggers` (items refers to itself).

1. Back up the live database (see [Backup](#backup)).
2. Apply the new file(s) in `supabase/migrations/` to live. Migrations must work with the code already live: add, never rename or drop, in the same change.
3. Merge to `main`. Vercel deploys the website.
4. Run `.\scripts\live-worker-update.ps1`, which does all of this: in `C:\apps\ReadURList`, `git pull`; stop the worker with `Stop-Process -Id <pid>` (find it with `Get-CimInstance Win32_Process -Filter "name='readurlist.exe'"`; "End" in Task Scheduler stops only the launcher); `uv sync`; then **Run** the "ReadURList Worker" task and check exactly one `readurlist.exe` runs, from `C:\apps\ReadURList`.
5. Check the change works on the live bot or website.

Without a database change, skip steps 1–2.

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

Three tabs: **Today** (the day’s list: Short reads and Long read, each pick with its reason, points per part and reading time, then Fallen off since the last list, then a "Last 7 days" line: picks read of picks shown, the verdict (working if at least half are read), skipped, and the unread pile then → now; sidebar is that day’s subjects/tags), **All** (library), **Unfetched** (stubs). Light/dark theme. `/unread` and `/topics` redirect into All.

**All:** filters All / Unread / Stale 14+ / Read / Skipped, and a second row Any length / Short / Long (combines with the first). Each card shows its effort label, e.g. "Short · 4 min" (230 words a minute; short is under 15 minutes; no word count counts as short in the filter). Unread is the ranking queue (ready, not skipped). Cards can mark read, skip, or restore. Edit can overwrite headline, description, subject, and topics, or **Send to Unfetched** after confirm. **Organize** (button on All, not a tab) merges singleton labels, batch-edits subject/topics, and lists the oldest unread items.

**Unfetched:** lists items the worker could not retrieve. Open **Paste article**, paste text or upload a PDF (max 3.5 MB — Vercel serverless limit). Saved text is ingested on the worker at the next daily digest (or when you run `/digest` / `readurlist-digest`). Stubs are hidden from Today and All until ingest completes.

**Held:** before the model reads a page (or pasted text), the worker scans it for text that looks like it instructs the AI. A match is saved as **held**, not read, and listed on Unfetched with the reason. **Release** reads it at the next daily run without the scan; **Delete** removes it. The model has no tools either way, and its answer is rejected unless it fits the fixed form.

## Backup

The corpus is in Supabase. Turn on backups in the project, or periodically dump with `supabase db dump` / `pg_dump`.

A local SQLite file is not a backup once capture writes to Postgres.

## Models

Change Groq model: set `MODEL_INGEST` in `.env` and restart. Default is `openai/gpt-oss-120b` (Groq retired `llama-3.3-70b-versatile` for free/developer on 16 Aug 2026). Ingest is given the current subject/topic lists and prefers existing labels. Groq JSON uses structured outputs; prompts are truncated to stay under on-demand TPM.

## Tests

In the dev folder only (never in the live folder: `uv` re-syncs the environment the worker runs from):

```bash
uv sync --extra dev
uv run pytest -q
cd web && npm ci && npm test && npm run build
```

CI runs pytest on push. Website builds on Vercel.

Do not commit `.env`, `web/.env.local`, `web/node_modules`, `web/.next`, or `web/tsconfig.tsbuildinfo` (already gitignored).

## Stack

Python · `python-telegram-bot` · SQLAlchemy · Groq · trafilatura · Supabase Postgres · Next.js on Vercel
