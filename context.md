# context.md — ReadURList

## One-line pitch
Saved URLs become a personal reading corpus. Telegram captures them with an AI snapshot; a daily job ranks what you should actually read; a website reorganizes the backlog.

## What this is NOT (anti-goals)
- Not a connection-ping or corpus-Q&A product. Chat is capture + digest.
- Not a public multi-user app. The website is password-gated; the bot is allowlisted to one Telegram user.
- Not a recap machine. Daily picks must prefer unread items that represent dense topics in *your* backlog, not a restatement of one save.

## Core insight / why this exists
Read-later piles die because saving is easy and choosing what to read is not. This stage dumps open tabs into a database, tags them (subject / topics / keywords), and surfaces a short ranked list once a day.

## Core loop
1. **Capture**: Paste URL(s) in Telegram (any device). Worker on the always-on NUC.
2. **Ingest**: Fetch, extract, Groq snapshot + subject/topics/keywords/priority; reuse the growing subject/topic vocabulary; store in Supabase.
3. **Rank** (daily): score the unread queue (`ready`, not skipped); write `daily_picks`.
4. **Digest**: Telegram message with top picks and Mark read / Skip buttons (at most once per day).
5. **Browse**: Vercel site reorganizes (Today, All, Unfetched). Mark read or skip there too.

## Ranking (weights)
Unread queue only (`read_at` and `skipped_at` both empty). Topic demand 0.45, recency 0.20, path novelty 0.20, LLM priority 0.15. Keywords stay specific and are display-only. Ingest prefers existing subjects. At most two picks per subject. Top 5. Skip leaves the queue without marking read.

## Success metric (personal)
Week two: are tabs actually closed, and do digest picks get marked read? If not, tune ranking before adding features.

## Deliberate omissions
Claim embeddings, connection pings, corpus Q&A, bookmarklet, public auth, FastAPI localhost UI, cloud worker hosting (Oracle/Fly). NUC is the host.
