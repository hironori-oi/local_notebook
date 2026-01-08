"""Add status and error_message fields to messages table.

Revision ID: 0027
Revises: 0026
Create Date: 2025-01-03

This migration adds:
- status: For tracking async message generation (pending, generating, completed, failed)
- error_message: For storing error details when generation fails
"""
from alembic import op
import sqlalchemy as sa


revision = "0027_add_message_status"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add status column with default 'completed' for existing messages
    op.add_column(
        "messages",
        sa.Column("status", sa.String(20), nullable=False, server_default="completed")
    )
    # Add index on status for efficient querying of pending messages
    op.create_index("ix_messages_status", "messages", ["status"])

    # Add error_message column for storing failure details
    op.add_column(
        "messages",
        sa.Column("error_message", sa.Text(), nullable=True)
    )


def downgrade() -> None:
    op.drop_index("ix_messages_status", table_name="messages")
    op.drop_column("messages", "error_message")
    op.drop_column("messages", "status")
