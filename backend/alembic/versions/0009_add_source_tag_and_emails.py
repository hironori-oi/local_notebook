"""add source tag and generated_emails table

Revision ID: 0009_add_source_tag_and_emails
Revises: 0008_add_slide_decks
Create Date: 2025-12-04

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0009_add_source_tag_and_emails"
down_revision = "0008_add_slide_decks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add tag column to sources table
    op.add_column("sources", sa.Column("tag", sa.String(20), nullable=True))
    op.create_check_constraint(
        "ck_sources_tag_valid",
        "sources",
        "tag IS NULL OR tag IN ('document', 'minutes')"
    )

    # Create generated_emails table
    op.create_table(
        "generated_emails",
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
        sa.Column("topic", sa.String(500), nullable=True),
        sa.Column("email_body", sa.Text, nullable=False),
        sa.Column("structured_content", postgresql.JSONB, nullable=True),
        sa.Column("document_source_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column("minutes_source_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
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
    op.create_index("ix_generated_emails_notebook_id", "generated_emails", ["notebook_id"])
    op.create_index("ix_generated_emails_created_by", "generated_emails", ["created_by"])


def downgrade() -> None:
    op.drop_index("ix_generated_emails_created_by", table_name="generated_emails")
    op.drop_index("ix_generated_emails_notebook_id", table_name="generated_emails")
    op.drop_table("generated_emails")

    op.drop_constraint("ck_sources_tag_valid", "sources", type_="check")
    op.drop_column("sources", "tag")
