"""CouncilMeeting model for managing council meeting sessions (開催回)."""
import uuid
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.base import Base


class CouncilMeeting(Base):
    """
    Represents a single meeting session of a council (第X回).

    Each meeting can have multiple agenda items (議題), where each agenda item
    has its own materials (資料) and minutes (議事録).
    """
    __tablename__ = "council_meetings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    council_id = Column(
        UUID(as_uuid=True),
        ForeignKey("councils.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    meeting_number = Column(Integer, nullable=False)  # 第X回
    title = Column(String(255), nullable=True)  # 開催名（オプション）
    scheduled_at = Column(DateTime(timezone=True), nullable=False)  # 開催日時

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    council = relationship("Council", back_populates="meetings")
    agendas = relationship(
        "CouncilAgendaItem",
        back_populates="meeting",
        cascade="all, delete-orphan",
        order_by="CouncilAgendaItem.agenda_number",
    )
    notes = relationship(
        "CouncilNote",
        back_populates="meeting",
        cascade="all, delete-orphan",
        order_by="desc(CouncilNote.created_at)",
    )
    # chunks は council_agenda_chunks に移行済みのため削除
    infographics = relationship(
        "CouncilInfographic",
        back_populates="meeting",
        cascade="all, delete-orphan",
    )
