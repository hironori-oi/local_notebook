"""CouncilAgendaMaterial model for managing multiple materials per agenda item."""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class CouncilAgendaMaterial(Base):
    """
    Represents a single material (資料) within an agenda item.

    Each agenda item can have multiple materials, each with its own URL,
    processed text, summary, and processing status.
    """

    __tablename__ = "council_agenda_materials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agenda_id = Column(
        UUID(as_uuid=True),
        ForeignKey("council_agenda_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    material_number = Column(Integer, nullable=False)  # 資料番号（agenda内でユニーク）
    title = Column(String(255), nullable=True)  # 資料タイトル（任意）

    # Source type: "url" for URL-based materials, "file" for uploaded files
    source_type = Column(String(10), nullable=False, default="url")

    # URL (nullable when source_type is "file")
    url = Column(String(2048), nullable=True)  # 資料URL

    # File upload fields (used when source_type is "file")
    file_path = Column(String(500), nullable=True)  # Storage path for uploaded file
    original_filename = Column(String(255), nullable=True)  # Original filename

    # Fetched text content
    text = Column(Text, nullable=True)  # 取得した資料テキスト

    # LLM-generated summary
    summary = Column(Text, nullable=True)  # 資料要約

    # Processing status tracking (pending/processing/completed/failed)
    processing_status = Column(String(20), nullable=False, default="pending")
    processing_error = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    agenda = relationship("CouncilAgendaItem", back_populates="materials")
    chunks = relationship(
        "CouncilAgendaChunk",
        back_populates="material",
        cascade="all, delete-orphan",
        foreign_keys="CouncilAgendaChunk.material_id",
    )
