"""One-shot schema sync for environments without Alembic.

Creates any missing tables and ALTERs existing tables to add any columns
that exist on the SQLAlchemy models but are missing in the database.

Safe to run multiple times. Does NOT drop or rename anything.
"""
from sqlalchemy import inspect, text

from app.db.models import Base
from app.db.session import engine


def main() -> int:
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
