"""add chat_sessions table and session_id to messages

Revision ID: 0005_add_chat_sessions
Revises: 0004_add_audit_logs
Create Date: 2025-11-30 12:00:00

This migration adds session-based conversation management:
- Creates chat_sessions table to group related messages
- Adds session_id foreign key to messages table
- Existing messages will have NULL session_id (backward compatible)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0005_add_chat_sessions"
down_revision = "0004_add_audit_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create chat_sessions table
    op.create_table(
        "chat_sessions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "notebook_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("notebooks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # Create indexes for chat_sessions
    op.create_index(
        "ix_chat_sessions_notebook_id",
        "chat_sessions",
        ["notebook_id"]
    )
    op.create_index(
        "ix_chat_sessions_user_id",
        "chat_sessions",
        ["user_id"]
    )
    op.create_index(
        "ix_chat_sessions_updated_at",
        "chat_sessions",
        ["updated_at"]
    )

    # Add session_id column to messages table
    op.add_column(
        "messages",
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"),
            nullable=True,  # Nullable for backward compatibility
        )
    )

    # Create index for session_id in messages
    op.create_index(
        "ix_messages_session_id",
        "messages",
        ["session_id"]
    )


def downgrade() -> None:
    # Drop index from messages
    op.drop_index("ix_messages_session_id", table_name="messages")

    # Drop session_id column from messages
    op.drop_column("messages", "session_id")

    # Drop indexes from chat_sessions
    op.drop_index("ix_chat_sessions_updated_at", table_name="chat_sessions")
    op.drop_index("ix_chat_sessions_user_id", table_name="chat_sessions")
    op.drop_index("ix_chat_sessions_notebook_id", table_name="chat_sessions")

    # Drop chat_sessions table
    op.drop_table("chat_sessions")
