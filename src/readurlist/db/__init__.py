from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from sqlalchemy.types import TypeDecorator


class StringList(TypeDecorator):
    """text[] on Postgres, JSON array on SQLite."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(ARRAY(Text))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        if value is None:
            return []
        return list(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return []
        return list(value)


class Base(DeclarativeBase):
    pass


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    url: Mapped[str] = mapped_column(String(2048), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(1024))
    snapshot: Mapped[str] = mapped_column(Text, default="")
    subject: Mapped[str] = mapped_column(String(256), default="")
    topics: Mapped[list[str]] = mapped_column(StringList, default=list)
    keywords: Mapped[list[str]] = mapped_column(StringList, default=list)
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[int] = mapped_column(Integer, default=3)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ingest_status: Mapped[str] = mapped_column(String(32), default="ready")
    similar_to_item_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("items.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    skipped_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class DailyPick(Base):
    __tablename__ = "daily_picks"
    __table_args__ = (UniqueConstraint("run_on", "item_id", name="uq_daily_picks_run_item"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_on: Mapped[date] = mapped_column(Date, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    rank: Mapped[int] = mapped_column(Integer)
    score: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(Text)

    item: Mapped[Item] = relationship()


class DigestRun(Base):
    __tablename__ = "digest_runs"

    run_on: Mapped[date] = mapped_column(Date, primary_key=True)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


_engine = None
SessionLocal = None


def init_db(database_url: str, *, create: bool | None = None) -> None:
    """Bind the engine. create_all only for SQLite (tests / local leftover DBs).

    Postgres schema comes from supabase/migrations — do not silent-create in prod.
    """
    global _engine, SessionLocal
    is_sqlite = database_url.startswith("sqlite")
    if is_sqlite:
        from pathlib import Path

        path = database_url.removeprefix("sqlite:///")
        if path and path != ":memory:" and not path.startswith("/"):
            Path(path).parent.mkdir(parents=True, exist_ok=True)
    connect_args = {"check_same_thread": False} if is_sqlite else {}
    _engine = create_engine(database_url, connect_args=connect_args)
    SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    should_create = create if create is not None else is_sqlite
    if should_create:
        Base.metadata.create_all(_engine)
        if is_sqlite:
            _migrate_sqlite(_engine)


def _migrate_sqlite(engine) -> None:
    """Add new columns on leftover SQLite files from V1."""
    with engine.begin() as conn:
        rows = conn.exec_driver_sql("PRAGMA table_info(items)").fetchall()
        columns = {row[1] for row in rows}
        alters = {
            "snapshot": "ALTER TABLE items ADD COLUMN snapshot TEXT DEFAULT ''",
            "subject": "ALTER TABLE items ADD COLUMN subject VARCHAR(256) DEFAULT ''",
            "topics": "ALTER TABLE items ADD COLUMN topics JSON DEFAULT '[]'",
            "keywords": "ALTER TABLE items ADD COLUMN keywords JSON DEFAULT '[]'",
            "priority": "ALTER TABLE items ADD COLUMN priority INTEGER DEFAULT 3",
            "note": "ALTER TABLE items ADD COLUMN note TEXT",
            "similar_to_item_id": "ALTER TABLE items ADD COLUMN similar_to_item_id INTEGER",
            "read_at": "ALTER TABLE items ADD COLUMN read_at DATETIME",
            "ingest_status": "ALTER TABLE items ADD COLUMN ingest_status VARCHAR(32) NOT NULL DEFAULT 'ready'",
            "skipped_at": "ALTER TABLE items ADD COLUMN skipped_at DATETIME",
        }
        for name, sql in alters.items():
            if name not in columns:
                conn.exec_driver_sql(sql)
        conn.exec_driver_sql(
            "UPDATE items SET ingest_status = 'ready' "
            "WHERE ingest_status IS NULL OR ingest_status = ''"
        )
        if "summary_one_liner" in columns:
            conn.exec_driver_sql(
                "UPDATE items SET snapshot = summary_one_liner "
                "WHERE (snapshot IS NULL OR snapshot = '') "
                "AND summary_one_liner IS NOT NULL AND summary_one_liner != ''"
            )


def get_session():
    if SessionLocal is None:
        raise RuntimeError("Database not initialized; call init_db first")
    return SessionLocal()


def reset_engine() -> None:
    global _engine, SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    SessionLocal = None


def mark_item_read(item_id: int, *, read: bool, when: datetime | None = None) -> Item | None:
    session = get_session()
    try:
        item = session.get(Item, item_id)
        if item is None:
            return None
        if read:
            item.read_at = when or datetime.now().astimezone()
        else:
            item.read_at = None
        session.commit()
        session.refresh(item)
        session.expunge(item)
        return item
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def mark_item_skipped(item_id: int, *, skipped: bool, when: datetime | None = None) -> Item | None:
    session = get_session()
    try:
        item = session.get(Item, item_id)
        if item is None:
            return None
        if skipped:
            item.skipped_at = when or datetime.now().astimezone()
        else:
            item.skipped_at = None
        session.commit()
        session.refresh(item)
        session.expunge(item)
        return item
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
