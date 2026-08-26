# Fetch-failure stub + Unfetched fill-in

**Date:** 2026-08-26  
**Issue:** Airtable #12 (ReadURList)  
**Status:** Approved for implementation planning

## Problem

When Telegram ingest cannot fetch or extract an article, the URL is never saved. The bot only reports the error. The URL is lost unless the user pastes it again later.

## Goal

1. On fetch/extract failure, still save the URL (plus any available page info such as a headline) as an incomplete corpus item.
2. Leave snapshot, subject, and tags as unavailable — no Groq call on this path.
3. Telegram tells the user the bot could not retrieve the article and to fill it in on the website.
4. Website has a dedicated Unfetched page with a Paste article flow (textarea or PDF).
5. Groq stays on the NUC. LLM runs only after the user provides text or a PDF. Completion runs once a day with the digest job — no hurry.

## Non-goals

- Calling Groq from Vercel.
- Instant fill-in after paste (daily batch is enough).
- Re-fetching the URL from the NUC (user-supplied body is the source of truth for completion).
- Public multi-user upload or auth beyond the existing site password gate.
- Changing ranking weights or digest copy beyond excluding incomplete items.

## Data model

Add `ingest_status` on `items`:

| Value | Meaning |
|-------|---------|
| `ready` | Fully ingested; eligible for ranking, Topics, Clusters, digest |
| `pending_body` | Stub from failed fetch/extract, or body submitted and awaiting NUC summary |

Migration (Supabase + SQLAlchemy/SQLite test path):

- Column: `ingest_status varchar not null default 'ready'`
- Existing rows backfill to `ready`
- Index optional: `(ingest_status)` for the daily completion query

Stub field conventions when creating `pending_body` with no article text yet:

| Field | Value |
|-------|--------|
| `url` | As pasted |
| `title` | HTML `<title>` / trafilatura metadata title if HTML was obtained; else the URL |
| `snapshot` | Literal `not available` |
| `subject` | Literal `not available` |
| `topics` | `[]` |
| `keywords` | `[]` |
| `extracted_text` | `''` until the user pastes / uploads |
| `priority` | Default `3` |
| `note` | Short fetch/extract error message (for Unfetched UI and debugging) |
| `ingest_status` | `pending_body` |

After website paste/PDF:

- `extracted_text` set to the provided body (trimmed)
- `ingest_status` remains `pending_body` until the NUC summarizes
- Optional: append or set `note` to indicate source (`paste` / `pdf`) if useful; do not wipe the original fetch error unless replaced intentionally

After daily NUC completion:

- Fill `title`, `snapshot`, `subject`, `topics`, `keywords`, `priority` via existing `summarize_article`
- Keep `extracted_text` as provided
- Set `ingest_status` = `ready`
- Clear or leave `note` (prefer leave; UI can hide when ready)

## Capture path (NUC / Telegram)

### Failures that create a stub

1. `FetchError` after retries (HTTP errors, timeouts, transport failures).
2. Extract failure when HTML was fetched but trafilatura yields too little text (`ValueError` from `extract_article` today).

If HTML is available but body extraction fails, still attempt to keep the page title from metadata before stubbing.

### Success path

Unchanged: fetch → extract → Groq summarize → insert with `ingest_status=ready`.

### Dedup

Unchanged: same URL returns the existing row without re-fetch. A stub is not replaced by a second paste of the same URL; the user completes it via Unfetched.

### Telegram message on stub save

Something like:

> Saved, but the article could not be retrieved. Paste the text or a PDF on the Unfetched page: `{SITE_URL}/unfetched`

Requires new settings: `SITE_URL` (e.g. `https://….vercel.app`), documented in `.env.example` and README.

Do not call Groq on the stub path.

## Website

### Nav

New tab: **Unfetched** → `/unfetched`.

### `/unfetched` page

- Lists items where `ingest_status = 'pending_body'` (newest first).
- Show items waiting for body **and** items that already have `extracted_text` but are not yet `ready` (awaiting daily job), with distinct copy:
  - No body yet: Paste article control
  - Body present, still pending: “Queued for today’s fill-in” (or similar); paste control optional/disabled to avoid accidental overwrite, or allow replace — **allow replace** of `extracted_text` until `ready` so the user can fix a bad paste before the job runs.

### Paste article UX

- On each card: **Paste article** button.
- Click expands (same card): multiline textarea + PDF file input.
- Submit via server action (password-gated site already protects writes):
  - Text: write into `extracted_text`
  - PDF: extract text on Vercel (library such as `pdf-parse` or equivalent), then write into `extracted_text`
  - Reject empty body; surface a clear error if PDF has no extractable text
- No Groq on the website.
- Revalidate `/unfetched` (and other paths if stubs appear elsewhere).

### Other views

- Today / ranking / digest: exclude `pending_body`.
- Unread / All / Topics / Clusters: exclude `pending_body` from topic chips and cluster membership driven by tags; Unfetched is the home for stubs. Optionally still show stubs on All with a badge — **prefer hide from All/Unread/Topics/Clusters** so the corpus views stay “readable” items only; Unfetched owns the incomplete queue.

### `ItemCard`

- Support Unfetched-specific actions without cluttering normal cards (separate component or props for paste UI).

## Ranking and digest

- `persist_ranking` / `score_unread`: only items with `ingest_status = 'ready'` (and existing unread rules).
- Cluster rebuild: only `ready` items.
- Incomplete stubs must not appear as daily picks or dilute topic demand.

## Daily NUC completion job

Run **once per day** on the same schedule as the digest (or immediately before digest ranking in that job), not on a 30–60s poller.

Algorithm:

1. Select items where `ingest_status = 'pending_body'` AND `extracted_text` is non-empty (after trim).
2. For each: call existing `summarize_article` with URL, title hint, and `extracted_text`.
3. Update fields; set `ingest_status = 'ready'`.
4. Telegram allowlisted user: short ack per item (or a compact batch summary if many), e.g. filled in *title* from your paste/PDF.
5. Failures: log; leave item `pending_body` with note updated so it retries next day; do not delete the row.

If the digest already ran earlier and only completion is needed mid-day, `/digest` may also run completion first so a forced digest can pick up newly filled items the same day — **yes**: `/digest` and the scheduled job both run “complete pending bodies, then rank/send digest as today”.

## Config

| Env | Where | Purpose |
|-----|--------|---------|
| `SITE_URL` | NUC worker `.env` | Link in Telegram stub message |
| Existing Groq / DB | NUC | Unchanged |
| No new Groq key on Vercel | Website | PDF/text write only |

## Testing

- Ingest: fetch failure and extract failure persist stub with correct fields and `pending_body`; no LLM call.
- Dedup: re-pasting same URL returns existing stub.
- Ranking: stubs excluded from picks.
- Completion: item with `pending_body` + body becomes `ready` with snapshot/tags; Telegram path unit-tested where practical.
- Website: server action writes `extracted_text`; empty/PDF-empty rejected (unit or light integration as the web stack allows).

## Implementation order (for the plan)

1. Schema (`ingest_status`) + model defaults.
2. Stub create on fetch/extract failure + Telegram message + `SITE_URL`.
3. Ranking/digest filter.
4. Daily (and `/digest`) completion pass.
5. `/unfetched` page + Paste article (text then PDF).
6. Docs / changelog / `.env.example`.

## Decisions log

- Groq remains on the NUC only.
- LLM triggers only after user provides text or PDF.
- Dedicated Unfetched page (not only an inline badge on Unread).
- Completion cadence: once daily with digest — not continuous polling.
- Approach: stub + website paste/PDF + NUC summarize (not Storage-first PDFs; extract text on submit).
