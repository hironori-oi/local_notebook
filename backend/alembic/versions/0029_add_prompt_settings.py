"""Add prompt_settings column to llm_settings table.

Revision ID: 0029_prompt_settings
Revises: 0028_agenda_materials
Create Date: 2025-01-04

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0029_prompt_settings'
down_revision = '0028_agenda_materials'
branch_labels = None
depends_on = None

# Default prompt settings
DEFAULT_PROMPT_SETTINGS = {
    "council_materials_system": None,
    "council_materials_user": None,
    "council_minutes_system": None,
    "council_minutes_user": None,
}


def upgrade() -> None:
    # Add prompt_settings column to llm_settings table
    op.add_column(
        'llm_settings',
        sa.Column(
            'prompt_settings',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text(f"'{{}}'::jsonb")
        )
    )


def downgrade() -> None:
    op.drop_column('llm_settings', 'prompt_settings')
