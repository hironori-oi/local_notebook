"""Add file upload support to council agenda materials

Revision ID: 0030
Revises: 0029
Create Date: 2026-02-01

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0030_material_file_upload"
down_revision = "0029_prompt_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add source_type column (default 'url' for existing records)
    op.add_column(
        "council_agenda_materials",
        sa.Column(
            "source_type",
            sa.String(10),
            nullable=False,
            server_default="url",
        ),
    )

    # Add file_path column for storing uploaded file location
    op.add_column(
        "council_agenda_materials",
        sa.Column("file_path", sa.String(500), nullable=True),
    )

    # Add original_filename column for display purposes
    op.add_column(
        "council_agenda_materials",
        sa.Column("original_filename", sa.String(255), nullable=True),
    )

    # Make url nullable (it's null when source_type is 'file')
    op.alter_column(
        "council_agenda_materials",
        "url",
        existing_type=sa.String(2048),
        nullable=True,
    )


def downgrade() -> None:
    # Delete file-based materials (they have no URL, so can't make url non-nullable)
    op.execute(
        "DELETE FROM council_agenda_materials WHERE source_type = 'file'"
    )

    # Remove added columns
    op.drop_column("council_agenda_materials", "original_filename")
    op.drop_column("council_agenda_materials", "file_path")
    op.drop_column("council_agenda_materials", "source_type")

    # Make url non-nullable again (safe after deleting file-based records)
    op.alter_column(
        "council_agenda_materials",
        "url",
        existing_type=sa.String(2048),
        nullable=False,
    )
