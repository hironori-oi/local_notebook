"""Add council_infographics table

Revision ID: 0021_add_council_infographics
Revises: 0020_add_note_content_field
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0021_add_council_infographics'
down_revision: Union[str, None] = '0020_add_note_content_field'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'council_infographics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('council_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('councils.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('meeting_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('council_meetings.id', ondelete='CASCADE'), nullable=True, index=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('topic', sa.String(500), nullable=True),
        sa.Column('structure', postgresql.JSONB, nullable=False),
        sa.Column('style_preset', sa.String(50), server_default='default'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('council_infographics')
