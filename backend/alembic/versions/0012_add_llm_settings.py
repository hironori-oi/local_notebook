"""add llm_settings table for user-configurable LLM settings

Revision ID: 0012_add_llm_settings
Revises: 0011_add_summary_fields
Create Date: 2025-12-05

This migration adds the llm_settings table to store user-specific LLM configurations:
- Provider settings (ollama, vllm, openai, anthropic)
- API base URL and encrypted API key
- Default model and embedding settings
- Feature-specific settings (chat, format, summary, email, infographic)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision = "0012_add_llm_settings"
down_revision = "0011_add_summary_fields"
branch_labels = None
depends_on = None

# Default feature settings as JSON string for PostgreSQL (single line for SQL compatibility)
DEFAULT_FEATURE_SETTINGS_JSON = '{"chat": {"model": null, "temperature": 0.1, "max_tokens": 4096}, "format": {"model": null, "temperature": 0.1, "max_tokens": 8192}, "summary": {"model": null, "temperature": 0.2, "max_tokens": 8192}, "email": {"model": null, "temperature": 0.3, "max_tokens": 8192}, "infographic": {"model": null, "temperature": 0.3, "max_tokens": 8192}}'


def upgrade() -> None:
    # Create llm_settings table
    op.create_table(
        "llm_settings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True, unique=True),

        # Basic LLM settings
        sa.Column("provider", sa.String(50), nullable=False, server_default="ollama"),
        sa.Column("api_base_url", sa.String(500), nullable=False, server_default="http://localhost:11434/v1"),
        sa.Column("api_key_encrypted", sa.Text, nullable=True),
        sa.Column("default_model", sa.String(200), nullable=False, server_default="gpt-oss-120b"),

        # Embedding settings
        sa.Column("embedding_model", sa.String(200), nullable=False, server_default="embeddinggemma:300m"),
        sa.Column("embedding_api_base", sa.String(500), nullable=False, server_default="http://localhost:11434/v1"),
        sa.Column("embedding_dim", sa.Integer, nullable=False, server_default="768"),

        # Feature-specific settings (JSONB)
        sa.Column("feature_settings", JSONB, nullable=False, server_default=sa.text(f"'{DEFAULT_FEATURE_SETTINGS_JSON}'::jsonb")),

        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Create index for user_id
    op.create_index("ix_llm_settings_user_id", "llm_settings", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_llm_settings_user_id", table_name="llm_settings")
    op.drop_table("llm_settings")
