"""Add composite indexes for common query patterns

Revision ID: 0024_add_composite_indexes
Revises: 0023_add_slide_generator_tables
Create Date: 2025-12-31

This migration adds composite indexes to improve query performance for:
- Processing status queries (sources, minutes)
- User's notebooks ordered by creation date
- Chat messages ordered by creation date
- User activity audit logs
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "0024_add_composite_indexes"
down_revision = "0023_add_slide_generator_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Sources: frequently filtered by notebook_id + processing_status
    op.create_index(
        "ix_sources_notebook_processing",
        "sources",
        ["notebook_id", "processing_status"],
    )

    # Sources: notebook_id + created_at for ordering
    op.create_index(
        "ix_sources_notebook_created",
        "sources",
        ["notebook_id", "created_at"],
    )

    # Minutes: frequently filtered by notebook_id + processing_status
    op.create_index(
        "ix_minutes_notebook_processing",
        "minutes",
        ["notebook_id", "processing_status"],
    )

    # Minutes: notebook_id + created_at for ordering
    op.create_index(
        "ix_minutes_notebook_created",
        "minutes",
        ["notebook_id", "created_at"],
    )

    # Messages: session_id + created_at for chat message ordering
    op.create_index(
        "ix_messages_session_created",
        "messages",
        ["session_id", "created_at"],
    )

    # Notebooks: owner_id + created_at for user's notebooks list
    op.create_index(
        "ix_notebooks_owner_created",
        "notebooks",
        ["owner_id", "created_at"],
    )

    # Audit logs: user_id + created_at for user activity timeline
    op.create_index(
        "ix_audit_logs_user_created",
        "audit_logs",
        ["user_id", "created_at"],
    )

    # Chat sessions: notebook_id + updated_at for recent sessions
    op.create_index(
        "ix_chat_sessions_notebook_updated",
        "chat_sessions",
        ["notebook_id", "updated_at"],
    )

    # Council meetings: council_id + scheduled_at (composite for ordering)
    op.create_index(
        "ix_council_meetings_council_scheduled",
        "council_meetings",
        ["council_id", "scheduled_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_council_meetings_council_scheduled", "council_meetings")
    op.drop_index("ix_chat_sessions_notebook_updated", "chat_sessions")
    op.drop_index("ix_audit_logs_user_created", "audit_logs")
    op.drop_index("ix_notebooks_owner_created", "notebooks")
    op.drop_index("ix_messages_session_created", "messages")
    op.drop_index("ix_minutes_notebook_created", "minutes")
    op.drop_index("ix_minutes_notebook_processing", "minutes")
    op.drop_index("ix_sources_notebook_created", "sources")
    op.drop_index("ix_sources_notebook_processing", "sources")
