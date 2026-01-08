"""add summary and processing fields for email generation

Revision ID: 0011_add_summary_fields
Revises: 0010_add_minutes_tables
Create Date: 2025-12-05

This migration adds fields to support summary-based email generation:
- Sources: full_text, formatted_text, summary, processing_status, processing_error
- Minutes: formatted_content, summary, processing_status, processing_error

These fields enable pre-generated summaries for email generation while
maintaining chunk-based RAG for chat functionality.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0011_add_summary_fields"
down_revision = "0010_add_minutes_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add content processing fields to sources table
    op.add_column("sources", sa.Column("full_text", sa.Text, nullable=True))
    op.add_column("sources", sa.Column("formatted_text", sa.Text, nullable=True))
    op.add_column("sources", sa.Column("summary", sa.Text, nullable=True))
    op.add_column(
        "sources",
        sa.Column(
            "processing_status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column("sources", sa.Column("processing_error", sa.Text, nullable=True))

    # Add content processing fields to minutes table
    op.add_column("minutes", sa.Column("formatted_content", sa.Text, nullable=True))
    op.add_column("minutes", sa.Column("summary", sa.Text, nullable=True))
    op.add_column(
        "minutes",
        sa.Column(
            "processing_status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column("minutes", sa.Column("processing_error", sa.Text, nullable=True))

    # Create index for processing_status to optimize queries for pending items
    op.create_index(
        "ix_sources_processing_status", "sources", ["processing_status"]
    )
    op.create_index(
        "ix_minutes_processing_status", "minutes", ["processing_status"]
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_minutes_processing_status", table_name="minutes")
    op.drop_index("ix_sources_processing_status", table_name="sources")

    # Remove columns from minutes
    op.drop_column("minutes", "processing_error")
    op.drop_column("minutes", "processing_status")
    op.drop_column("minutes", "summary")
    op.drop_column("minutes", "formatted_content")

    # Remove columns from sources
    op.drop_column("sources", "processing_error")
    op.drop_column("sources", "processing_status")
    op.drop_column("sources", "summary")
    op.drop_column("sources", "formatted_text")
    op.drop_column("sources", "full_text")
