"""Council model for managing deliberative councils (審議会)."""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Council(Base):
    """
    Represents a deliberative council (審議会).

    Councils are top-level entities that group multiple meetings,
    similar to how Notebooks group multiple sources.
    """

    __tablename__ = "councils"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    organization = Column(String(255), nullable=True)  # 所管省庁 (e.g., 経済産業省)
    council_type = Column(String(100), nullable=True)  # 部会/審議会/委員会
    official_url = Column(String(2048), nullable=True)  # 公式ページURL
    is_public = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    owner = relationship("User", backref="councils")
    meetings = relationship(
        "CouncilMeeting",
        back_populates="council",
        cascade="all, delete-orphan",
        order_by="desc(CouncilMeeting.scheduled_at)",
    )
    notes = relationship(
        "CouncilNote",
        back_populates="council",
        cascade="all, delete-orphan",
        order_by="desc(CouncilNote.created_at)",
    )
    chat_sessions = relationship(
        "CouncilChatSession",
        back_populates="council",
        cascade="all, delete-orphan",
        order_by="desc(CouncilChatSession.updated_at)",
    )
    infographics = relationship(
        "CouncilInfographic",
        back_populates="council",
        cascade="all, delete-orphan",
    )
