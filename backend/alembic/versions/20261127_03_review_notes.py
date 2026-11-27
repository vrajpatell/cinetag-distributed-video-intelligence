"""Add review notes with versioned updates and retry-safe creation."""

import sqlalchemy as sa
from alembic import op

revision = "20261127_03_review_notes"
down_revision = "20260511_02_list_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Some local installs bootstrap schema from the ORM before running migrations.
    if not sa.inspect(op.get_bind()).has_table("review_notes"):
        op.create_table(
            "review_notes",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("video_id", sa.Integer(), sa.ForeignKey("video_assets.id"), nullable=False),
            sa.Column("request_id", sa.String(36), nullable=False),
            sa.Column("request_hash", sa.String(64), nullable=False),
            sa.Column("category", sa.String(24), nullable=False),
            sa.Column("state", sa.String(16), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("position_ms", sa.Integer(), nullable=True),
            sa.Column("revision", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("video_id", "request_id", name="uq_review_note_request"),
        )
    op.create_index(
        "ix_review_notes_video_state",
        "review_notes",
        ["video_id", "state", "id"],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_table("review_notes")
