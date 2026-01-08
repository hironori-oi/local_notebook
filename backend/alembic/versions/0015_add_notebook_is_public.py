"""Add is_public column to notebooks table for public/private distinction

Revision ID: 0015_add_notebook_is_public
Revises: 0014_add_user_role
Create Date: 2025-12-10

This migration adds an is_public column to the notebooks table:
- is_public: Boolean flag (default: False)
- False: Only owner can access (private/personal notebook)
- True: All users can access and edit (public shared notebook)
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0015_add_notebook_is_public"
down_revision = "0014_add_user_role"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_public column to notebooks table with default value False
    op.add_column(
        "notebooks",
        sa.Column("is_public", sa.Boolean, nullable=False, server_default="false")
    )

    # Create index for is_public column for efficient filtering
    op.create_index("ix_notebooks_is_public", "notebooks", ["is_public"])


def downgrade() -> None:
    op.drop_index("ix_notebooks_is_public", table_name="notebooks")
    op.drop_column("notebooks", "is_public")
