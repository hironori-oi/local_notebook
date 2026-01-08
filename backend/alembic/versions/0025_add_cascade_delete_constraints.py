"""Add cascade delete constraints to foreign keys.

Revision ID: 0025
Revises: 0024
Create Date: 2024-01-01

This migration adds ON DELETE CASCADE to foreign keys that were missing it,
ensuring proper cleanup when parent records are deleted.
"""
from alembic import op


revision = "0025"
down_revision = "0024_add_composite_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # source_chunks.source_id -> CASCADE
    op.drop_constraint(
        "source_chunks_source_id_fkey", "source_chunks", type_="foreignkey"
    )
    op.create_foreign_key(
        "source_chunks_source_id_fkey",
        "source_chunks",
        "sources",
        ["source_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # sources.notebook_id -> CASCADE
    op.drop_constraint(
        "sources_notebook_id_fkey", "sources", type_="foreignkey"
    )
    op.create_foreign_key(
        "sources_notebook_id_fkey",
        "sources",
        "notebooks",
        ["notebook_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # sources.created_by -> CASCADE
    op.drop_constraint(
        "sources_created_by_fkey", "sources", type_="foreignkey"
    )
    op.create_foreign_key(
        "sources_created_by_fkey",
        "sources",
        "users",
        ["created_by"],
        ["id"],
        ondelete="CASCADE",
    )

    # notes.notebook_id -> CASCADE
    op.drop_constraint(
        "notes_notebook_id_fkey", "notes", type_="foreignkey"
    )
    op.create_foreign_key(
        "notes_notebook_id_fkey",
        "notes",
        "notebooks",
        ["notebook_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # notes.message_id -> CASCADE
    op.drop_constraint(
        "notes_message_id_fkey", "notes", type_="foreignkey"
    )
    op.create_foreign_key(
        "notes_message_id_fkey",
        "notes",
        "messages",
        ["message_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # notes.created_by -> CASCADE
    op.drop_constraint(
        "notes_created_by_fkey", "notes", type_="foreignkey"
    )
    op.create_foreign_key(
        "notes_created_by_fkey",
        "notes",
        "users",
        ["created_by"],
        ["id"],
        ondelete="CASCADE",
    )

    # note_sources.note_id -> CASCADE
    op.drop_constraint(
        "note_sources_note_id_fkey", "note_sources", type_="foreignkey"
    )
    op.create_foreign_key(
        "note_sources_note_id_fkey",
        "note_sources",
        "notes",
        ["note_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # note_sources.source_id -> CASCADE
    op.drop_constraint(
        "note_sources_source_id_fkey", "note_sources", type_="foreignkey"
    )
    op.create_foreign_key(
        "note_sources_source_id_fkey",
        "note_sources",
        "sources",
        ["source_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # notebooks.owner_id -> CASCADE
    op.drop_constraint(
        "notebooks_owner_id_fkey", "notebooks", type_="foreignkey"
    )
    op.create_foreign_key(
        "notebooks_owner_id_fkey",
        "notebooks",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    # Revert all constraints to no cascade behavior
    op.drop_constraint(
        "notebooks_owner_id_fkey", "notebooks", type_="foreignkey"
    )
    op.create_foreign_key(
        "notebooks_owner_id_fkey",
        "notebooks",
        "users",
        ["owner_id"],
        ["id"],
    )

    op.drop_constraint(
        "note_sources_source_id_fkey", "note_sources", type_="foreignkey"
    )
    op.create_foreign_key(
        "note_sources_source_id_fkey",
        "note_sources",
        "sources",
        ["source_id"],
        ["id"],
    )

    op.drop_constraint(
        "note_sources_note_id_fkey", "note_sources", type_="foreignkey"
    )
    op.create_foreign_key(
        "note_sources_note_id_fkey",
        "note_sources",
        "notes",
        ["note_id"],
        ["id"],
    )

    op.drop_constraint(
        "notes_created_by_fkey", "notes", type_="foreignkey"
    )
    op.create_foreign_key(
        "notes_created_by_fkey",
        "notes",
        "users",
        ["created_by"],
        ["id"],
    )

    op.drop_constraint(
        "notes_message_id_fkey", "notes", type_="foreignkey"
    )
    op.create_foreign_key(
        "notes_message_id_fkey",
        "notes",
        "messages",
        ["message_id"],
        ["id"],
    )

    op.drop_constraint(
        "notes_notebook_id_fkey", "notes", type_="foreignkey"
    )
    op.create_foreign_key(
        "notes_notebook_id_fkey",
        "notes",
        "notebooks",
        ["notebook_id"],
        ["id"],
    )

    op.drop_constraint(
        "sources_created_by_fkey", "sources", type_="foreignkey"
    )
    op.create_foreign_key(
        "sources_created_by_fkey",
        "sources",
        "users",
        ["created_by"],
        ["id"],
    )

    op.drop_constraint(
        "sources_notebook_id_fkey", "sources", type_="foreignkey"
    )
    op.create_foreign_key(
        "sources_notebook_id_fkey",
        "sources",
        "notebooks",
        ["notebook_id"],
        ["id"],
    )

    op.drop_constraint(
        "source_chunks_source_id_fkey", "source_chunks", type_="foreignkey"
    )
    op.create_foreign_key(
        "source_chunks_source_id_fkey",
        "source_chunks",
        "sources",
        ["source_id"],
        ["id"],
    )
