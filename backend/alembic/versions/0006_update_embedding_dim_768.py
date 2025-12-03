"""update embedding dimension to 768 for embeddinggemma:300m

Revision ID: 0006_update_embedding_dim_768
Revises: 0005_add_chat_sessions
Create Date: 2025-12-02 00:00:00

"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision = "0006_update_embedding_dim_768"
down_revision = "0005_add_chat_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the old embedding column and create with new dimension
    # Note: This will lose existing embeddings - run re-indexing after migration
    op.drop_column("source_chunks", "embedding")
    op.add_column(
        "source_chunks",
        sa.Column("embedding", Vector(dim=768), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("source_chunks", "embedding")
    op.add_column(
        "source_chunks",
        sa.Column("embedding", Vector(dim=2048), nullable=True),
    )
