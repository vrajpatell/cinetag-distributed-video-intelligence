"""One-shot schema sync for environments without Alembic.

Creates any missing tables and ALTERs existing tables to add any columns
that exist on the SQLAlchemy models but are missing in the database.

Safe to run multiple times. Does NOT drop or rename anything.
"""
import logging

from sqlalchemy import inspect, text
from sqlalchemy.exc import ProgrammingError

from app.db.models import Base
from app.db.session import engine

logger = logging.getLogger(__name__)


def _ensure_pgvector(conn) -> None:
    """Enable the pgvector extension if missing.

    On Cloud SQL Postgres the application user is usually not a superuser, so
    this will fail with InsufficientPrivilege. That's OK as long as a DB admin
    has already run ``CREATE EXTENSION vector`` once as the postgres user — the
    extension only needs to be created once per database.
    """
    try:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
    except ProgrammingError as exc:
        logger.warning(
            "Could not CREATE EXTENSION vector (%s). "
            "Run it once as the postgres superuser if pgvector columns are needed.",
            exc.orig.__class__.__name__,
        )


def main() -> int:
    with engine.begin() as conn:
        _ensure_pgvector(conn)

    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    dialect = engine.dialect

    added: list[str] = []
    with engine.begin() as conn:
        for table_name, table in Base.metadata.tables.items():
            if table_name not in inspector.get_table_names():
                continue
            existing_cols = {c["name"] for c in inspector.get_columns(table_name)}
            for column in table.columns:
                if column.name in existing_cols:
                    continue
                column_type = column.type.compile(dialect=dialect)
                sql = (
                    f'ALTER TABLE "{table_name}" '
                    f'ADD COLUMN IF NOT EXISTS "{column.name}" {column_type}'
                )
                conn.execute(text(sql))
                added.append(f"{table_name}.{column.name}")

    if added:
        print(f"schema sync added {len(added)} column(s):")
        for col in added:
            print(f"  - {col}")
    else:
        print("schema sync: no missing columns")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
