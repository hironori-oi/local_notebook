"""Add council agenda items and remove old meeting fields.

Revision ID: 0018
Revises: 0017
Create Date: 2024-12-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = '0018_add_council_agenda_items'
down_revision = '0017_add_council_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create council_agenda_items table
    op.create_table(
        'council_agenda_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('meeting_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('council_meetings.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('agenda_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('materials_url', sa.String(2048), nullable=True),
        sa.Column('minutes_url', sa.String(2048), nullable=True),
        sa.Column('materials_text', sa.Text(), nullable=True),
        sa.Column('minutes_text', sa.Text(), nullable=True),
        sa.Column('materials_summary', sa.Text(), nullable=True),
        sa.Column('minutes_summary', sa.Text(), nullable=True),
        sa.Column('materials_processing_status', sa.String(20),
                  nullable=False, server_default='pending'),
        sa.Column('minutes_processing_status', sa.String(20),
                  nullable=False, server_default='pending'),
        sa.Column('processing_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create unique constraint on meeting_id + agenda_number
    op.create_index(
        'ix_council_agenda_items_meeting_agenda',
        'council_agenda_items',
        ['meeting_id', 'agenda_number'],
        unique=True
    )

    # Create council_agenda_chunks table
    op.create_table(
        'council_agenda_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('agenda_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('council_agenda_items.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('chunk_type', sa.String(20), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(dim=768), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
    )

    # Drop council_meeting_chunks table (replaced by council_agenda_chunks)
    op.drop_table('council_meeting_chunks')

    # Remove old columns from council_meetings
    op.drop_column('council_meetings', 'materials_url')
    op.drop_column('council_meetings', 'minutes_url')
    op.drop_column('council_meetings', 'materials_text')
    op.drop_column('council_meetings', 'minutes_text')
    op.drop_column('council_meetings', 'materials_summary')
    op.drop_column('council_meetings', 'minutes_summary')
    op.drop_column('council_meetings', 'materials_processing_status')
    op.drop_column('council_meetings', 'minutes_processing_status')
    op.drop_column('council_meetings', 'processing_error')


def downgrade() -> None:
    # Add back columns to council_meetings
    op.add_column('council_meetings', sa.Column('materials_url', sa.String(2048), nullable=True))
    op.add_column('council_meetings', sa.Column('minutes_url', sa.String(2048), nullable=True))
    op.add_column('council_meetings', sa.Column('materials_text', sa.Text(), nullable=True))
    op.add_column('council_meetings', sa.Column('minutes_text', sa.Text(), nullable=True))
    op.add_column('council_meetings', sa.Column('materials_summary', sa.Text(), nullable=True))
    op.add_column('council_meetings', sa.Column('minutes_summary', sa.Text(), nullable=True))
    op.add_column('council_meetings', sa.Column('materials_processing_status',
                                                 sa.String(20), nullable=False, server_default='pending'))
    op.add_column('council_meetings', sa.Column('minutes_processing_status',
                                                 sa.String(20), nullable=False, server_default='pending'))
    op.add_column('council_meetings', sa.Column('processing_error', sa.Text(), nullable=True))

    # Recreate council_meeting_chunks table
    op.create_table(
        'council_meeting_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('meeting_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('council_meetings.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('chunk_type', sa.String(20), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(dim=768), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
    )

    # Drop council_agenda_chunks table
    op.drop_table('council_agenda_chunks')

    # Drop council_agenda_items table
    op.drop_index('ix_council_agenda_items_meeting_agenda', table_name='council_agenda_items')
    op.drop_table('council_agenda_items')
