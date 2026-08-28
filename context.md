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
3. **Rank** (daily): score unread items; write `daily_picks`.
4. **Digest**: Telegram message with top picks and Mark read buttons (at most once per day).
5. **Browse**: Vercel site reorganizes (Today, Unread, Topics, All, Path). Mark read there too.

## Ranking (weights)
Unread only. Topic demand 0.45, recency 0.20, path novelty 0.20, LLM priority 0.15. Keywords stay specific and are for near-duplicates. Ingest prefers existing subjects. Near-duplicates of already-read or of a stronger unread canonical are omitted. At most two picks per subject. Top 5.

## Success metric (personal)
Week two: are tabs actually closed, and do digest picks get marked read? If not, tune ranking before adding features.

## Deliberate omissions
Claim embeddings, connection pings, corpus Q&A, bookmarklet, public auth, FastAPI localhost UI, cloud worker hosting (Oracle/Fly). NUC is the host.
