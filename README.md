# ReadURList

Personal knowledge corpus over Telegram. Paste URLs, get short save-time acks, converse with your corpus, and receive rare pings when genuine claim-level connections appear.

See [context.md](context.md) for product principles and [CHANGELOG.md](CHANGELOG.md) for release history.

## Setup

1. **Create a Telegram bot** via [@BotFather](https://t.me/BotFather) → `/newbot`. Copy the token.
2. **Get your user id** via [@userinfobot](https://t.me/userinfobot).
3. **Python 3.11+** and a free [Groq API key](https://console.groq.com).

```bash
cd ReadURList
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
# edit .env: TELEGRAM_BOT_TOKEN, TELEGRAM_USER_ID, GROQ_API_KEY
```

Credentials needed: Telegram bot token, your Telegram user id, Groq API key.  
No OpenAI key — chat runs on Groq; embeddings run locally (`sentence-transformers`).

## Run locally

```bash
source .venv/bin/activate
second-read
# or: python -m second_read.main
```

First run downloads the local embed model (`all-MiniLM-L6-v2`) once.  
Then in Telegram: open your bot → `/start` → paste a URL.

## How it behaves

| You do | Bot does |
|--------|----------|
| Paste a URL | Fetches, extracts, stores claims; replies with **title + one-line summary** only |
| Ask a question | Answers **from your corpus** with source links — or says it can't |
| Wait | At most 1–2 pings/day in quiet hours, **only** when a real connection exists |

## Models

Per-task Groq model IDs in `.env` (`MODEL_INGEST`, `MODEL_CONNECT`, `MODEL_PING`, `MODEL_CONVERSE`).  
`MODEL_EMBED` is a local sentence-transformers model name. The LLM layer is an adapter — OpenAI provider remains available if you want to switch later.

## Stack

Python · `python-telegram-bot` · SQLite/SQLAlchemy · Groq · sentence-transformers · trafilatura
