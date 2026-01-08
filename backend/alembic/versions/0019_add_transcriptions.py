"""add transcriptions table

Revision ID: 0019_add_transcriptions
Revises: 0018_add_council_agenda_items
Create Date: 2025-12-13

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0019_add_transcriptions"
down_revision = "0018_add_council_agenda_items"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transcriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("youtube_url", sa.String(2048), nullable=False),
        sa.Column("video_id", sa.String(32), nullable=False),
        sa.Column("video_title", sa.String(500), nullable=True),
        sa.Column("raw_transcript", sa.Text, nullable=True),
        sa.Column("formatted_transcript", sa.Text, nullable=True),
        sa.Column("processing_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("processing_error", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # Create indexes for common queries
    op.create_index("ix_transcriptions_user_id", "transcriptions", ["user_id"])
    op.create_index("ix_transcriptions_video_id", "transcriptions", ["video_id"])
    op.create_index("ix_transcriptions_processing_status", "transcriptions", ["processing_status"])

    # Create check constraint for status values
    op.create_check_constraint(
        "ck_transcriptions_status_valid",
        "transcriptions",
        "processing_status IN ('pending', 'processing', 'completed', 'failed')"
    )


def downgrade() -> None:
    op.drop_constraint("ck_transcriptions_status_valid", "transcriptions", type_="check")
    op.drop_index("ix_transcriptions_processing_status", table_name="transcriptions")
    op.drop_index("ix_transcriptions_video_id", table_name="transcriptions")
    op.drop_index("ix_transcriptions_user_id", table_name="transcriptions")
    op.drop_table("transcriptions")
