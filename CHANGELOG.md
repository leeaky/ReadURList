# Changelog

All notable changes to ReadURList are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Product name from working title "Second Read" to **ReadURList** (docs, `/start` copy, packaging description).

### Added
- Meta corpus intents (DB-backed, no embedding gate): list saves, summarise/overview, are-related.
- Title + one-liner retrieval alongside claim embeddings for content questions.
- Article fetch hardening: browser-like headers, retries with backoff/`Retry-After` on 429/5xx, clearer rate-limit errors in Telegram.

### Fixed
- Softened converse similarity floor (0.25; small corpora keep top‑k) so borderline content questions reach Groq instead of the empty-corpus reply.

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
