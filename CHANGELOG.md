# Changelog

All notable changes to ReadURList are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Clusters browse is gone. Topics (by subject) is the grouping; ranking no longer uses cluster centrality (weights 0.45 / 0.20 / 0.20 / 0.15).
- Groq JSON calls use structured outputs, spend remaining TPM on completion tokens (gpt-oss reasoning), retry empty json_validate_failed, and consolidate from unique labels so the daily remap fits on-demand Groq.
- Ingest reuses existing ready subjects/topics; the daily job consolidates near-duplicate tags when unique subjects are more than half of ready items.
- Ranking clusters on subject + topics; keywords are only for near-duplicate detection.
- Today explains ranking and shows pick rank; Topics and Unread say how they relate.
- Edit can send a completed item back to Unfetched (clears the body, queues Groq fill-in).
- Product center from claim-connection pings to **capture → snapshot → daily ranked reads**.
- Ingest output is a 2–4 sentence snapshot plus subject, topics, keywords, and priority.
- Persistence target is **Supabase Postgres**; worker stays on the always-on NUC.
- Groq chat retries on 429/5xx during bulk ingest.
- Unfetched splits needs-text vs saved-for-fill-in; paste form closes on save; stubs can be deleted after confirm.
- Corpus cards can overwrite headline, description, subject, and topics when ingest captured the wrong page.
- Today’s topic/tag sidebar lists only that day’s picks. All and Organize show the full tag list (no 18-tag cap). Duplicate tags on one article are collapsed.

### Added
- Fetch/extract failures save `pending_body` stubs; Unfetched page for paste/PDF; daily NUC Groq fill-in before digest.
- Multi-URL paste in Telegram (sequential `n/N` snapshots).
- Daily cluster + ranking job, `daily_picks`, Telegram digest with Mark read buttons (`/digest` to run now).
- Next.js website (`web/`) on Vercel: Today, Unread, Topics, All, Unfetched, reading path, password gate, mark read.
- SQLite → Postgres migrate script; pytest suite and GitHub Action.

### Removed
- Localhost FastAPI browse UI (replaced by the Vercel site).
- Connect / converse / ping modules, claim embeddings, and `sentence-transformers`.
- Legacy item columns `summary_one_liner` and `surfaced_count`.

## [0.1.0] - 2026-07-11

### Added
- Telegram single-user bot (allowlisted user ID) as the only V1 surface.
- Capture + ingest: URL detect, trafilatura extract, Groq summarization + claim extraction, short save-time ack.
- Connect: embedding candidate recall + LLM relationship labeling (`contradicts` / `answers` / `extends` / `related`) with quality gate.
- Converse: corpus-grounded Q&A with source citations; honest empty answers when retrieval fails.
- Ping scheduler: jittered quiet-hour checks, ranked relationship selection, silence when no genuine hook.
- SQLite/SQLAlchemy persistence for items, claims, relationships, pings, and messages.
- LLM adapter with Groq chat + local `sentence-transformers` embeddings (`OpenAIProvider` retained for later swap).
- Project docs: `context.md`, `README.md`, `.env.example`.

[Unreleased]: https://github.com/leeaky/ReadURList/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/leeaky/ReadURList/releases/tag/v0.1.0
