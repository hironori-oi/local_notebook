"""add source_refs to messages table

Revision ID: 0003_add_message_sources
Revises: 0002_update_embedding_dim
Create Date: 2025-11-29 00:02:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0003_add_message_sources"
down_revision = "0002_update_embedding_dim"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add source_refs column to store referenced sources as JSON array
    op.add_column(
        "messages",
        sa.Column("source_refs", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("messages", "source_refs")
