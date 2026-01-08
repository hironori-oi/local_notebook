"""Add document_checker tables

Revision ID: 0022_add_document_checker_tables
Revises: 0021_add_council_infographics
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0022_add_document_checker_tables'
down_revision: Union[str, None] = '0021_add_council_infographics'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create document_checks table
    op.create_table(
        'document_checks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('file_type', sa.String(10), nullable=False),
        sa.Column('original_text', sa.Text, nullable=False),
        sa.Column('page_count', sa.Integer, nullable=True),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('check_types', postgresql.JSONB, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create document_check_issues table
    op.create_table(
        'document_check_issues',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('document_checks.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('severity', sa.String(20), server_default='warning'),
        sa.Column('page_or_slide', sa.Integer, nullable=True),
        sa.Column('line_number', sa.Integer, nullable=True),
        sa.Column('original_text', sa.Text, nullable=False),
        sa.Column('suggested_text', sa.Text, nullable=True),
        sa.Column('explanation', sa.Text, nullable=True),
        sa.Column('is_accepted', sa.Boolean, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Create user_check_preferences table
    op.create_table(
        'user_check_preferences',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True, index=True),
        sa.Column('default_check_types', postgresql.JSONB, server_default='[]'),
        sa.Column('custom_terminology', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('user_check_preferences')
    op.drop_table('document_check_issues')
    op.drop_table('document_checks')
