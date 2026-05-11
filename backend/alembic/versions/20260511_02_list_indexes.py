"""Add indexes for paginated list/filter queries.

Revision ID: 20260511_02_list_indexes
Revises: 20260509_01_pgvector_embeddings
"""

from alembic import op

revision = "20260511_02_list_indexes"
down_revision = "20260509_01_pgvector_embeddings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_video_assets_status",
        "video_assets",
        ["status"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "ix_processing_jobs_status",
        "processing_jobs",
        ["status"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "ix_processing_jobs_created_at",
        "processing_jobs",
        ["created_at"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "ix_generated_tags_status",
        "generated_tags",
        ["status"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "ix_generated_tags_tag_type",
        "generated_tags",
        ["tag_type"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "ix_generated_tags_video_id",
        "generated_tags",
        ["video_id"],
        unique=False,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_generated_tags_video_id", table_name="generated_tags", if_exists=True)
    op.drop_index("ix_generated_tags_tag_type", table_name="generated_tags", if_exists=True)
    op.drop_index("ix_generated_tags_status", table_name="generated_tags", if_exists=True)
    op.drop_index("ix_processing_jobs_created_at", table_name="processing_jobs", if_exists=True)
    op.drop_index("ix_processing_jobs_status", table_name="processing_jobs", if_exists=True)
    op.drop_index("ix_video_assets_status", table_name="video_assets", if_exists=True)
