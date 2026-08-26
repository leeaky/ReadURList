# Changelog

All notable changes to ReadURList are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Product center from claim-connection pings to **capture → snapshot → daily ranked reads**.
- Ingest output is a 2–4 sentence snapshot plus subject, topics, keywords, and priority.
- Persistence target is **Supabase Postgres**; worker stays on the always-on NUC.
- Groq chat retries on 429/5xx during bulk ingest.

### Added
- Fetch/extract failures save `pending_body` stubs; Unfetched page for paste/PDF; daily NUC Groq fill-in before digest.
- Multi-URL paste in Telegram (sequential `n/N` snapshots).
- Daily cluster + ranking job, `daily_picks`, Telegram digest with Mark read buttons (`/digest` to run now).
- Next.js website (`web/`) on Vercel: Today, Unread, Topics, Clusters, All, Unfetched, reading path, password gate, mark read.
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
