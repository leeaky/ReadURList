from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker


class Base(DeclarativeBase):
    pass


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    url: Mapped[str] = mapped_column(String(2048), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(1024))
    extracted_text: Mapped[str] = mapped_column(Text)
    summary_one_liner: Mapped[str] = mapped_column(String(1024))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    surfaced_count: Mapped[int] = mapped_column(Integer, default=0)

    claims: Mapped[list[Claim]] = relationship(back_populates="item")


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    embedding_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    item: Mapped[Item] = relationship(back_populates="claims")


class Relationship(Base):
    __tablename__ = "relationships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    claim_a_id: Mapped[int] = mapped_column(ForeignKey("claims.id"), index=True)
    claim_b_id: Mapped[int] = mapped_column(ForeignKey("claims.id"), index=True)
    type: Mapped[str] = mapped_column(String(32))  # contradicts|answers|extends|related
    strength: Mapped[float] = mapped_column(Float, default=0.5)
    rationale: Mapped[str] = mapped_column(Text)
    surfaced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    claim_a: Mapped[Claim] = relationship(foreign_keys=[claim_a_id])
    claim_b: Mapped[Claim] = relationship(foreign_keys=[claim_b_id])


class Ping(Base):
    __tablename__ = "pings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    relationship_id: Mapped[int] = mapped_column(ForeignKey("relationships.id"))
    hook: Mapped[str] = mapped_column(Text)
    analysis: Mapped[str] = mapped_column(Text)
    question: Mapped[str] = mapped_column(Text)
    sent_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    replied_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    relationship: Mapped[Relationship] = relationship()


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_message_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    role: Mapped[str] = mapped_column(String(16))  # user|assistant|system
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Meta(Base):
    __tablename__ = "meta"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[str] = mapped_column(Text)


_engine = None
SessionLocal = None


def init_db(database_url: str) -> None:
    global _engine, SessionLocal
    if database_url.startswith("sqlite:///"):
        from pathlib import Path

        path = database_url.removeprefix("sqlite:///")
        if path and path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    _engine = create_engine(database_url, connect_args=connect_args)
    SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(_engine)


def get_session():
    if SessionLocal is None:
        raise RuntimeError("Database not initialized; call init_db first")
    return SessionLocal()
