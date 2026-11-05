"""SQLAlchemy session. PostgreSQL in production, SQLite only for the demo/tests."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.settings import database_url

_engine = None
_Session = None


class Base(DeclarativeBase):
    pass


def get_engine():
    global _engine, _Session
    if _engine is None:
        url = database_url()
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)
        _Session = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
    return _engine


def reset_engine() -> None:
    """Drop the cached engine. Tests call this after pointing DATABASE_URL elsewhere."""
    global _engine, _Session
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _Session = None


def session_factory():
    get_engine()
    return _Session


def db_session() -> Iterator[Session]:
    factory = session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()


def init_db() -> None:
    # Import models so they register on Base.metadata before create_all.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=get_engine())
