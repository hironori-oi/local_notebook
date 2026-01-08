"""add minutes tables and remove source tag

Revision ID: 0010_add_minutes_tables
Revises: 0009_add_source_tag_and_emails
Create Date: 2025-12-05

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = "0010_add_minutes_tables"
down_revision = "0009_add_source_tag_and_emails"
branch_labels = None
depends_on = None

# Must match settings.EMBEDDING_DIM
EMBEDDING_DIM = 768


def upgrade() -> None:
    # 1. Create minutes table (text-based meeting minutes)
    op.create_table(
        "minutes",
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
        sa.Column("content", sa.Text, nullable=False),
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
    op.create_index("ix_minutes_notebook_id", "minutes", ["notebook_id"])
    op.create_index("ix_minutes_created_by", "minutes", ["created_by"])

    # 2. Create minute_documents junction table (link minutes to sources)
    op.create_table(
        "minute_documents",
        sa.Column(
            "minute_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("minutes.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sources.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # 3. Create minute_chunks table for RAG
    op.create_table(
        "minute_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "minute_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("minutes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_minute_chunks_minute_id", "minute_chunks", ["minute_id"])

    # 4. Drop tag column from sources table (no longer needed)
    op.drop_constraint("ck_sources_tag_valid", "sources", type_="check")
    op.drop_column("sources", "tag")

    # 5. Modify generated_emails: rename minutes_source_ids to minute_ids
    op.alter_column(
        "generated_emails",
        "minutes_source_ids",
        new_column_name="minute_ids",
    )


def downgrade() -> None:
    # Reverse minute_ids rename
    op.alter_column(
        "generated_emails",
        "minute_ids",
        new_column_name="minutes_source_ids",
    )

    # Add back tag column to sources
    op.add_column("sources", sa.Column("tag", sa.String(20), nullable=True))
    op.create_check_constraint(
        "ck_sources_tag_valid",
        "sources",
        "tag IS NULL OR tag IN ('document', 'minutes')"
    )

    # Drop minute_chunks
    op.drop_index("ix_minute_chunks_minute_id", table_name="minute_chunks")
    op.drop_table("minute_chunks")

    # Drop minute_documents
    op.drop_table("minute_documents")

    # Drop minutes
    op.drop_index("ix_minutes_created_by", table_name="minutes")
    op.drop_index("ix_minutes_notebook_id", table_name="minutes")
    op.drop_table("minutes")
