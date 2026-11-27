from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError


@pytest.fixture()
def migration():
    path = (
        Path(__file__).resolve().parents[3] / "alembic" / "versions" / "20261127_03_review_notes.py"
    )
    spec = spec_from_file_location("review_notes_migration", path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migrate_existing_catalog_and_downgrade(migration):
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE video_assets (id INTEGER PRIMARY KEY, title VARCHAR(255))"))
        conn.execute(text("INSERT INTO video_assets VALUES (1, 'Existing asset')"))
        with Operations.context(MigrationContext.configure(conn)):
            migration.upgrade()
            tables = inspect(conn)
            assert tables.has_table("review_notes")
            assert {i["name"] for i in tables.get_indexes("review_notes")} == {
                "ix_review_notes_video_state"
            }
            constraints = tables.get_unique_constraints("review_notes")
            assert constraints[0]["column_names"] == ["video_id", "request_id"]
            assert tables.get_foreign_keys("review_notes")[0]["referred_table"] == "video_assets"
            migration.downgrade()
            assert not inspect(conn).has_table("review_notes")
            assert (
                conn.execute(text("SELECT title FROM video_assets")).scalar_one()
                == "Existing asset"
            )


def test_upgrade_after_orm_bootstrap_preserves_notes(migration, db_engine):
    with db_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO review_notes "
                "(video_id, request_id, request_hash, category, state, body, revision, created_at, updated_at) "
                "VALUES (1, 'existing-request', 'abc', 'editorial', 'open', 'existing note', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
        with Operations.context(MigrationContext.configure(conn)):
            migration.upgrade()
        assert conn.execute(text("SELECT body FROM review_notes")).scalar_one() == "existing note"
        with pytest.raises(IntegrityError):
            conn.execute(
                text(
                    "INSERT INTO review_notes "
                    "(video_id, request_id, request_hash, category, state, body, revision, created_at, updated_at) "
                    "SELECT video_id, request_id, request_hash, category, state, body, revision, created_at, updated_at FROM review_notes"
                )
            )
