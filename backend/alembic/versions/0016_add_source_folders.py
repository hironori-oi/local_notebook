"""Add source_folders table and folder_id to sources

Revision ID: 0016_add_source_folders
Revises: 0015_add_notebook_is_public
Create Date: 2025-12-10

This migration adds folder management for sources:
- source_folders: Table for organizing sources within a notebook
- sources.folder_id: Foreign key to source_folders (nullable, CASCADE delete)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0016_add_source_folders"
down_revision = "0015_add_notebook_is_public"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create source_folders table
    op.create_table(
        "source_folders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "notebook_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("notebooks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("position", sa.Integer, nullable=False, server_default="0"),
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
    op.create_index("ix_source_folders_notebook_id", "source_folders", ["notebook_id"])

    # Add folder_id to sources table
    op.add_column(
        "sources",
        sa.Column(
            "folder_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_folders.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.create_index("ix_sources_folder_id", "sources", ["folder_id"])


def downgrade() -> None:
    op.drop_index("ix_sources_folder_id", table_name="sources")
    op.drop_column("sources", "folder_id")
    op.drop_index("ix_source_folders_notebook_id", table_name="source_folders")
    op.drop_table("source_folders")
