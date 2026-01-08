"""Add slide generator tables

Revision ID: 0023_add_slide_generator_tables
Revises: 0022_add_document_checker_tables
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0023_add_slide_generator_tables'
down_revision: Union[str, None] = '0022_add_document_checker_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create slide_templates table first (referenced by slide_projects)
    op.create_table(
        'slide_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('slide_count', sa.Integer, nullable=False),
        sa.Column('layout_info', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Create slide_styles table (referenced by slide_projects)
    op.create_table(
        'slide_styles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('settings', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('is_default', sa.Integer, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create slide_projects table
    op.create_table(
        'slide_projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('source_text', sa.Text, nullable=False),
        sa.Column('target_slide_count', sa.Integer, nullable=True),
        sa.Column('key_points', sa.Text, nullable=True),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('slide_templates.id', ondelete='SET NULL'), nullable=True),
        sa.Column('style_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('slide_styles.id', ondelete='SET NULL'), nullable=True),
        sa.Column('status', sa.String(20), server_default='draft'),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create slide_contents table
    op.create_table(
        'slide_contents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('slide_projects.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('slide_number', sa.Integer, nullable=False),
        sa.Column('slide_type', sa.String(50), server_default='content'),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('content', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('speaker_notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create slide_messages table
    op.create_table(
        'slide_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('slide_projects.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('slide_messages')
    op.drop_table('slide_contents')
    op.drop_table('slide_projects')
    op.drop_table('slide_styles')
    op.drop_table('slide_templates')
