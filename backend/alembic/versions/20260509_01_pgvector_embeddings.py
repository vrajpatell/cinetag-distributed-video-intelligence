"""Add pgvector-backed embedding column.

Revision ID: 20260509_01_pgvector_embeddings
Revises:
Create Date: 2026-05-09
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260509_01_pgvector_embeddings"
down_revision = None
branch_labels = None
depends_on = None


class Vector1536(sa.types.UserDefinedType):
    def get_col_spec(self, **_kw):
        return "VECTOR(1536)"


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.add_column(
        "embedding_records",
        sa.Column("embedding_vector", Vector1536(), nullable=True),
    )
    op.add_column(
        "embedding_records",
        sa.Column("embedding_model", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "embedding_records",
        sa.Column("embedding_provider", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "embedding_records",
        sa.Column("embedding_dimension", sa.Integer(), nullable=True),
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_embedding_records_vector_hnsw
        ON embedding_records
        USING hnsw (embedding_vector vector_cosine_ops);
        """
    )
    op.execute(
        """
        UPDATE embedding_records
        SET embedding_dimension = jsonb_array_length(embedding::jsonb)
        WHERE embedding_dimension IS NULL;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_embedding_records_vector_hnsw;")
    op.drop_column("embedding_records", "embedding_dimension")
    op.drop_column("embedding_records", "embedding_provider")
    op.drop_column("embedding_records", "embedding_model")
    op.drop_column("embedding_records", "embedding_vector")
