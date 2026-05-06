"""Shared pytest fixtures.

The fixtures here keep tests fast and DB-free by routing the API's
``get_db`` dependency at a fresh in-memory SQLite database, and stubbing the
GCS-backed object store with an in-memory dictionary so the upload flow can
be exercised end-to-end without network or credentials.
"""

from __future__ import annotations

import os
from typing import Generator

# These env vars must be set BEFORE app modules are imported so SQLAlchemy and
# pydantic-settings pick them up cleanly. ``setdefault`` keeps any explicit
# overrides supplied by callers.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("STORAGE_BACKEND", "minio")
os.environ.setdefault("CORS_ALLOWED_ORIGINS", "http://localhost:3000")
os.environ.setdefault("MAX_UPLOAD_SIZE_MB", "1024")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db import models  # noqa: E402,F401  (registers tables on Base.metadata)
from app.db.session import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def db_engine():
    # ``StaticPool`` keeps a single in-memory SQLite connection alive across
    # the test, so the FastAPI request thread and the assertions thread share
    # the same database. Without it each new thread would see an empty DB.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture()
def db_session(db_engine) -> Generator:
    SessionLocal = sessionmaker(
        bind=db_engine, autoflush=False, autocommit=False, future=True
    )
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_engine) -> Generator[TestClient, None, None]:
    SessionLocal = sessionmaker(
        bind=db_engine, autoflush=False, autocommit=False, future=True
    )

    def _override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)
