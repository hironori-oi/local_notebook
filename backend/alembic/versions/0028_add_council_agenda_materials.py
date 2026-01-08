"""Add council_agenda_materials table for multiple materials per agenda item.

Revision ID: 0028
Revises: 0027
Create Date: 2025-01-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0028_agenda_materials'
down_revision = '0027_add_message_status'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create council_agenda_materials table
    op.create_table(
        'council_agenda_materials',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('agenda_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('council_agenda_items.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('material_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('url', sa.String(2048), nullable=False),
        sa.Column('text', sa.Text(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('processing_status', sa.String(20),
                  nullable=False, server_default='pending'),
        sa.Column('processing_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create unique constraint on agenda_id + material_number
    op.create_index(
        'ix_council_agenda_materials_agenda_number',
        'council_agenda_materials',
        ['agenda_id', 'material_number'],
        unique=True
    )

    # Add material_id column to council_agenda_chunks
    op.add_column(
        'council_agenda_chunks',
        sa.Column('material_id', postgresql.UUID(as_uuid=True), nullable=True)
    )

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_council_agenda_chunks_material_id',
        'council_agenda_chunks',
        'council_agenda_materials',
        ['material_id'],
        ['id'],
        ondelete='CASCADE'
    )

    # Add index for material_id
    op.create_index(
        'ix_council_agenda_chunks_material_id',
        'council_agenda_chunks',
        ['material_id']
    )


def downgrade() -> None:
    # Drop index on material_id
    op.drop_index('ix_council_agenda_chunks_material_id', table_name='council_agenda_chunks')

    # Drop foreign key constraint
    op.drop_constraint('fk_council_agenda_chunks_material_id', 'council_agenda_chunks', type_='foreignkey')

    # Drop material_id column from council_agenda_chunks
    op.drop_column('council_agenda_chunks', 'material_id')

    # Drop council_agenda_materials table
    op.drop_index('ix_council_agenda_materials_agenda_number', table_name='council_agenda_materials')
    op.drop_table('council_agenda_materials')
