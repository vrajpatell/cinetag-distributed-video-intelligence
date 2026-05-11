from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings

_engine = None
SessionLocal = sessionmaker(autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_engine():
    """Lazily create the SQLAlchemy engine after secrets/config bootstrap."""
    global _engine
    if _engine is None:
        url = get_settings().effective_database_url
        _engine = create_engine(url, future=True)
        SessionLocal.configure(bind=_engine)
    return _engine


def get_db():
    get_engine()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
