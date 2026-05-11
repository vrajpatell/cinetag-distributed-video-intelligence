"""Add pgvector-backed embedding column.

Revision ID: 20260509_01_pgvector_embeddings
Revises:
Create Date: 2026-05-09
"""

import sqlalchemy as sa
from alembic import op

revision = "20260509_01_pgvector_embeddings"
down_revision = None
branch_labels = None
depends_on = None


class Vector1536(sa.types.UserDefinedType):
    def get_col_spec(self, **_kw):
        return "VECTOR(1536)"


def upgrade() -> None:
    bind = op.get_bind()
    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector;"))
    insp = sa.inspect(bind)
    if "embedding_records" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("embedding_records")}
    if "embedding_vector" not in cols:
        op.add_column(
            "embedding_records",
            sa.Column("embedding_vector", Vector1536(), nullable=True),
        )
    if "embedding_model" not in cols:
        op.add_column(
            "embedding_records",
            sa.Column("embedding_model", sa.String(length=128), nullable=True),
        )
    if "embedding_provider" not in cols:
        op.add_column(
            "embedding_records",
            sa.Column("embedding_provider", sa.String(length=64), nullable=True),
        )
    if "embedding_dimension" not in cols:
        op.add_column(
            "embedding_records",
            sa.Column("embedding_dimension", sa.Integer(), nullable=True),
        )

    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
              CREATE INDEX IF NOT EXISTS ix_embedding_records_vector_hnsw
              ON embedding_records
              USING hnsw (embedding_vector vector_cosine_ops);
            EXCEPTION WHEN OTHERS THEN
              RAISE NOTICE 'hnsw index skipped: %', SQLERRM;
            END $$;
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE embedding_records
            SET embedding_dimension = jsonb_array_length(embedding::jsonb)
            WHERE embedding_dimension IS NULL AND embedding IS NOT NULL;
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS ix_embedding_records_vector_hnsw;"))
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "embedding_records" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("embedding_records")}
    if "embedding_dimension" in cols:
        op.drop_column("embedding_records", "embedding_dimension")
    if "embedding_provider" in cols:
        op.drop_column("embedding_records", "embedding_provider")
    if "embedding_model" in cols:
        op.drop_column("embedding_records", "embedding_model")
    if "embedding_vector" in cols:
        op.drop_column("embedding_records", "embedding_vector")
