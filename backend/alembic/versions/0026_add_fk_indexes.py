"""Add indexes to foreign key columns for better query performance.

Revision ID: 0026
Revises: 0025
Create Date: 2024-01-01

This migration adds indexes to foreign key columns that are frequently
used in queries but were missing indexes.
"""
from alembic import op
from sqlalchemy import text


revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def create_index_if_not_exists(index_name: str, table_name: str, columns: list[str]) -> None:
    """Create index only if it doesn't already exist."""
    conn = op.get_bind()
    result = conn.execute(
        text(
            "SELECT 1 FROM pg_indexes WHERE indexname = :name"
        ),
        {"name": index_name}
    )
    if result.fetchone() is None:
        op.create_index(index_name, table_name, columns)


def upgrade() -> None:
    # source_chunks.source_id - frequently queried for RAG
    create_index_if_not_exists(
        "ix_source_chunks_source_id",
        "source_chunks",
        ["source_id"],
    )

    # notes.notebook_id - for listing notes in a notebook
    create_index_if_not_exists(
        "ix_notes_notebook_id",
        "notes",
        ["notebook_id"],
    )

    # notes.message_id - for finding notes by message
    create_index_if_not_exists(
        "ix_notes_message_id",
        "notes",
        ["message_id"],
    )

    # sources.folder_id - for counting sources per folder
    create_index_if_not_exists(
        "ix_sources_folder_id",
        "sources",
        ["folder_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_sources_folder_id", "sources")
    op.drop_index("ix_notes_message_id", "notes")
    op.drop_index("ix_notes_notebook_id", "notes")
    op.drop_index("ix_source_chunks_source_id", "source_chunks")
