"""add slide_decks table

Revision ID: 0008_add_slide_decks
Revises: 0007_add_infographics
Create Date: 2025-12-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0008_add_slide_decks"
down_revision = "0007_add_infographics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "slide_decks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "notebook_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("notebooks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("topic", sa.String(500), nullable=True),
        sa.Column("outline", postgresql.JSONB, nullable=False),
        sa.Column("pptx_path", sa.String(500), nullable=True),
        sa.Column("slide_count", sa.Integer, server_default="0"),
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
    op.create_index("ix_slide_decks_notebook_id", "slide_decks", ["notebook_id"])
    op.create_index("ix_slide_decks_created_by", "slide_decks", ["created_by"])


def downgrade() -> None:
    op.drop_index("ix_slide_decks_created_by", table_name="slide_decks")
    op.drop_index("ix_slide_decks_notebook_id", table_name="slide_decks")
    op.drop_table("slide_decks")
