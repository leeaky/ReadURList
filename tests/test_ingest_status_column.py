from sqlalchemy import create_engine, text

from second_read.db import Item, get_session, init_db


def test_sqlite_migration_ingest_status_not_null(tmp_path):
    db_path = tmp_path / "legacy.db"
    url = f"sqlite:///{db_path}"
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE items (
                    id INTEGER PRIMARY KEY,
                    url VARCHAR(2048) UNIQUE NOT NULL,
                    title VARCHAR(1024) NOT NULL,
                    extracted_text TEXT DEFAULT '',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
    engine.dispose()

    init_db(url)

    engine = create_engine(url)
    with engine.connect() as conn:
        rows = conn.execute(text("PRAGMA table_info(items)")).fetchall()
    engine.dispose()

    ingest_col = next(row for row in rows if row[1] == "ingest_status")
    assert ingest_col[3] == 1  # notnull


def test_new_item_defaults_ingest_status_ready(tmp_path):
    init_db(f"sqlite:///{tmp_path / 't.db'}")
    session = get_session()
    try:
        item = Item(url="https://example.com/a", title="A")
        session.add(item)
        session.commit()
        session.refresh(item)
        assert item.ingest_status == "ready"
    finally:
        session.close()
