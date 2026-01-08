"""CouncilAgendaItem model for managing agenda items within a council meeting."""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class CouncilAgendaItem(Base):
    """
    Represents a single agenda item within a council meeting.

    Each agenda item can have materials (資料) and minutes (議事録) URLs,
    along with their processed text and LLM-generated summaries.
    Multiple agenda items can exist for one meeting.
    """

    __tablename__ = "council_agenda_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(
        UUID(as_uuid=True),
        ForeignKey("council_meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agenda_number = Column(Integer, nullable=False)  # 議題番号（meeting内でユニーク）
    title = Column(String(255), nullable=True)  # 議題タイトル（任意）

    # URLs for external resources
    materials_url = Column(String(2048), nullable=True)  # 資料URL
    minutes_url = Column(String(2048), nullable=True)  # 議事録URL

    # Fetched text content
    materials_text = Column(Text, nullable=True)  # 取得した資料テキスト
    minutes_text = Column(Text, nullable=True)  # 取得した議事録テキスト

    # LLM-generated summaries
    materials_summary = Column(Text, nullable=True)  # 資料要約
    minutes_summary = Column(Text, nullable=True)  # 議事録要約

    # Processing status tracking (pending/processing/completed/failed)
    materials_processing_status = Column(String(20), nullable=False, default="pending")
    minutes_processing_status = Column(String(20), nullable=False, default="pending")
    processing_error = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    meeting = relationship("CouncilMeeting", back_populates="agendas")
    chunks = relationship(
        "CouncilAgendaChunk",
        back_populates="agenda",
        cascade="all, delete-orphan",
    )
    materials = relationship(
        "CouncilAgendaMaterial",
        back_populates="agenda",
        cascade="all, delete-orphan",
        order_by="CouncilAgendaMaterial.material_number",
    )
