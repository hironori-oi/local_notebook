"""Add role column to users table for admin/user distinction

Revision ID: 0014_add_user_role
Revises: 0013_add_search_indexes
Create Date: 2025-12-10

This migration adds a role column to the users table:
- role: "admin" or "user" (default: "user")
- Existing users will be assigned the "user" role
- The first user can be promoted to admin via environment variable or manually
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0014_add_user_role"
down_revision = "0013_add_search_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add role column to users table with default value "user"
    op.add_column(
        "users",
        sa.Column("role", sa.String(20), nullable=False, server_default="user")
    )

    # Create index for role column for efficient filtering
    op.create_index("ix_users_role", "users", ["role"])


def downgrade() -> None:
    op.drop_index("ix_users_role", table_name="users")
    op.drop_column("users", "role")
