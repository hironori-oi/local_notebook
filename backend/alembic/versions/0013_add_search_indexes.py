"""Add PostgreSQL GIN indexes for full-text search

Revision ID: 0013_add_search_indexes
Revises: 0012_add_llm_settings
Create Date: 2025-12-05

This migration adds GIN indexes for fast full-text search across:
- Notebooks (title, description)
- Sources (title)
- Minutes (title, content)
- Messages (content)

Using PostgreSQL's full-text search with 'simple' configuration for
Japanese text support.
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "0013_add_search_indexes"
down_revision = "0012_add_llm_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create GIN indexes for full-text search
    # Using 'simple' configuration which works better for CJK (Chinese/Japanese/Korean) text

    # Notebooks - search by title and description
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_notebooks_title_gin
        ON notebooks
        USING gin(to_tsvector('simple', title))
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_notebooks_description_gin
        ON notebooks
        USING gin(to_tsvector('simple', COALESCE(description, '')))
    """)

    # Sources - search by title
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_sources_title_gin
        ON sources
        USING gin(to_tsvector('simple', title))
    """)

    # Minutes - search by title and content
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_minutes_title_gin
        ON minutes
        USING gin(to_tsvector('simple', title))
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_minutes_content_gin
        ON minutes
        USING gin(to_tsvector('simple', COALESCE(content, '')))
    """)

    # Messages - search by content
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_messages_content_gin
        ON messages
        USING gin(to_tsvector('simple', content))
    """)

    # Also create standard B-tree indexes for ILIKE queries (fallback)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_notebooks_title_btree
        ON notebooks (title varchar_pattern_ops)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_sources_title_btree
        ON sources (title varchar_pattern_ops)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_minutes_title_btree
        ON minutes (title varchar_pattern_ops)
    """)


def downgrade() -> None:
    # Drop GIN indexes
    op.execute("DROP INDEX IF EXISTS ix_notebooks_title_gin")
    op.execute("DROP INDEX IF EXISTS ix_notebooks_description_gin")
    op.execute("DROP INDEX IF EXISTS ix_sources_title_gin")
    op.execute("DROP INDEX IF EXISTS ix_minutes_title_gin")
    op.execute("DROP INDEX IF EXISTS ix_minutes_content_gin")
    op.execute("DROP INDEX IF EXISTS ix_messages_content_gin")

    # Drop B-tree indexes
    op.execute("DROP INDEX IF EXISTS ix_notebooks_title_btree")
    op.execute("DROP INDEX IF EXISTS ix_sources_title_btree")
    op.execute("DROP INDEX IF EXISTS ix_minutes_title_btree")
