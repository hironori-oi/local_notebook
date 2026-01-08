"""add council management tables

Revision ID: 0017_add_council_tables
Revises: 0016_add_source_folders
Create Date: 2025-12-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = "0017_add_council_tables"
down_revision = "0016_add_source_folders"
branch_labels = None
depends_on = None

# Must match settings.EMBEDDING_DIM
EMBEDDING_DIM = 768


def upgrade() -> None:
    # 1. Create councils table
    op.create_table(
        "councils",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("organization", sa.String(255), nullable=True),  # 所管省庁
        sa.Column("council_type", sa.String(100), nullable=True),  # 部会/審議会/委員会
        sa.Column("official_url", sa.String(2048), nullable=True),  # 公式ページURL
        sa.Column("is_public", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_councils_owner_id", "councils", ["owner_id"])
    op.create_index("ix_councils_is_public", "councils", ["is_public"])

    # 2. Create council_meetings table
    op.create_table(
        "council_meetings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "council_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("councils.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("meeting_number", sa.Integer, nullable=False),  # 第X回
        sa.Column("title", sa.String(255), nullable=True),  # 開催名（オプション）
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),  # 開催日時
        sa.Column("materials_url", sa.String(2048), nullable=True),  # 資料URL
        sa.Column("minutes_url", sa.String(2048), nullable=True),  # 議事録URL
        # 取得したテキスト
        sa.Column("materials_text", sa.Text, nullable=True),
        sa.Column("minutes_text", sa.Text, nullable=True),
        # LLM要約
        sa.Column("materials_summary", sa.Text, nullable=True),
        sa.Column("minutes_summary", sa.Text, nullable=True),
        # 処理ステータス
        sa.Column(
            "materials_processing_status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "minutes_processing_status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("processing_error", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_council_meetings_council_id", "council_meetings", ["council_id"])
    op.create_index("ix_council_meetings_scheduled_at", "council_meetings", ["scheduled_at"])

    # 3. Create council_meeting_chunks table for RAG
    op.create_table(
        "council_meeting_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "meeting_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("council_meetings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_type", sa.String(20), nullable=False),  # materials or minutes
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_council_meeting_chunks_meeting_id", "council_meeting_chunks", ["meeting_id"])
    op.create_index("ix_council_meeting_chunks_chunk_type", "council_meeting_chunks", ["chunk_type"])

    # 4. Create council_notes table
    op.create_table(
        "council_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "council_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("councils.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "meeting_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("council_meetings.id", ondelete="CASCADE"),
            nullable=True,  # NULL = council-level note
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_council_notes_council_id", "council_notes", ["council_id"])
    op.create_index("ix_council_notes_meeting_id", "council_notes", ["meeting_id"])
    op.create_index("ix_council_notes_user_id", "council_notes", ["user_id"])

    # 5. Create council_chat_sessions table
    op.create_table(
        "council_chat_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "council_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("councils.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("selected_meeting_ids", postgresql.JSON, nullable=True),  # Array of meeting UUIDs
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_council_chat_sessions_council_id", "council_chat_sessions", ["council_id"])
    op.create_index("ix_council_chat_sessions_user_id", "council_chat_sessions", ["user_id"])

    # 6. Create council_messages table
    op.create_table(
        "council_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("council_chat_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),  # user or assistant
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("source_refs", postgresql.JSON, nullable=True),  # Array of meeting references
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_council_messages_session_id", "council_messages", ["session_id"])


def downgrade() -> None:
    # Drop council_messages
    op.drop_index("ix_council_messages_session_id", table_name="council_messages")
    op.drop_table("council_messages")

    # Drop council_chat_sessions
    op.drop_index("ix_council_chat_sessions_user_id", table_name="council_chat_sessions")
    op.drop_index("ix_council_chat_sessions_council_id", table_name="council_chat_sessions")
    op.drop_table("council_chat_sessions")

    # Drop council_notes
    op.drop_index("ix_council_notes_user_id", table_name="council_notes")
    op.drop_index("ix_council_notes_meeting_id", table_name="council_notes")
    op.drop_index("ix_council_notes_council_id", table_name="council_notes")
    op.drop_table("council_notes")

    # Drop council_meeting_chunks
    op.drop_index("ix_council_meeting_chunks_chunk_type", table_name="council_meeting_chunks")
    op.drop_index("ix_council_meeting_chunks_meeting_id", table_name="council_meeting_chunks")
    op.drop_table("council_meeting_chunks")

    # Drop council_meetings
    op.drop_index("ix_council_meetings_scheduled_at", table_name="council_meetings")
    op.drop_index("ix_council_meetings_council_id", table_name="council_meetings")
    op.drop_table("council_meetings")

    # Drop councils
    op.drop_index("ix_councils_is_public", table_name="councils")
    op.drop_index("ix_councils_owner_id", table_name="councils")
    op.drop_table("councils")
