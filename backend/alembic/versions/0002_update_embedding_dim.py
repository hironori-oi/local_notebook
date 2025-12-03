"""update embedding dimension to 2048 for PLaMo-Embedding-1B

Revision ID: 0002_update_embedding_dim
Revises: 0001_init_tables
Create Date: 2025-11-29 00:01:00

"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision = "0002_update_embedding_dim"
down_revision = "0001_init_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the old embedding column and create with new dimension
    # Note: This will lose existing embeddings - run re-indexing after migration
    op.drop_column("source_chunks", "embedding")
    op.add_column(
        "source_chunks",
        sa.Column("embedding", Vector(dim=2048), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("source_chunks", "embedding")
    op.add_column(
        "source_chunks",
        sa.Column("embedding", Vector(dim=1536), nullable=True),
    )
