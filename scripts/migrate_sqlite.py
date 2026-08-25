"""Copy V1 SQLite items into Postgres (Supabase).

Usage:
  python -m scripts.migrate_sqlite ./data/second_read.db

Requires DATABASE_URL in the environment pointing at Postgres.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

from second_read.config import get_settings
from second_read.db import Item, get_session, init_db


def migrate(sqlite_path: Path) -> int:
    settings = get_settings()
    if settings.database_url.startswith("sqlite"):
        raise SystemExit("DATABASE_URL must be Postgres (Supabase), not SQLite")
    init_db(settings.database_url, create=False)
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM items").fetchall()
    conn.close()

    session = get_session()
    inserted = 0
    try:
        for row in rows:
            url = row["url"]
            if session.query(Item).filter_by(url=url).one_or_none():
                continue
            snapshot = ""
            keys = row.keys()
            if "snapshot" in keys and row["snapshot"]:
                snapshot = row["snapshot"]
            elif "summary_one_liner" in keys and row["summary_one_liner"]:
                snapshot = row["summary_one_liner"]
            topics = []
            keywords = []
            if "topics" in keys and row["topics"]:
                raw = row["topics"]
                topics = json.loads(raw) if isinstance(raw, str) and raw.startswith("[") else []
            if "keywords" in keys and row["keywords"]:
                raw = row["keywords"]
                keywords = json.loads(raw) if isinstance(raw, str) and raw.startswith("[") else []
            item = Item(
                url=url,
                title=row["title"] or url,
                snapshot=snapshot,
                subject=row["subject"] if "subject" in keys and row["subject"] else "",
                topics=topics,
                keywords=keywords,
                extracted_text=row["extracted_text"] if "extracted_text" in keys else "",
                priority=int(row["priority"]) if "priority" in keys and row["priority"] else 3,
                note=row["note"] if "note" in keys else None,
            )
            session.add(item)
            inserted += 1
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    return inserted


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python -m scripts.migrate_sqlite PATH_TO_SQLITE_DB")
    path = Path(sys.argv[1])
    if not path.exists():
        raise SystemExit(f"No such file: {path}")
    n = migrate(path)
    print(f"Inserted {n} item(s) into Postgres")


if __name__ == "__main__":
    main()
