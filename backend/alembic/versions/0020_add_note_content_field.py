"""Add content and updated_at fields to notes table.

Revision ID: 0020_add_note_content_field
Revises: 0019_add_transcriptions
Create Date: 2024-01-01

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0020_add_note_content_field'
down_revision = '0019_add_transcriptions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add content column for user-editable note content
    op.add_column('notes', sa.Column('content', sa.Text(), nullable=True))
    # Add updated_at column to track when notes are edited
    op.add_column('notes', sa.Column(
        'updated_at',
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=True
    ))


def downgrade() -> None:
    op.drop_column('notes', 'updated_at')
    op.drop_column('notes', 'content')
