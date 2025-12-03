"""add infographics table

Revision ID: 0007_add_infographics
Revises: 0006_update_embedding_dim_768
Create Date: 2025-12-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0007_add_infographics"
down_revision = "0006_update_embedding_dim_768"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "infographics",
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
        sa.Column("structure", postgresql.JSONB, nullable=False),
        sa.Column("style_preset", sa.String(50), server_default="default"),
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
    op.create_index("ix_infographics_notebook_id", "infographics", ["notebook_id"])
    op.create_index("ix_infographics_created_by", "infographics", ["created_by"])


def downgrade() -> None:
    op.drop_index("ix_infographics_created_by", table_name="infographics")
    op.drop_index("ix_infographics_notebook_id", table_name="infographics")
    op.drop_table("infographics")
