import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.sql import func

from app.db.base import Base


class GeneratedEmail(Base):
    __tablename__ = "generated_emails"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    notebook_id = Column(
        UUID(as_uuid=True),
        ForeignKey("notebooks.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_by = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title = Column(String(255), nullable=False)
    topic = Column(String(500), nullable=True)
    email_body = Column(Text, nullable=False)
    structured_content = Column(JSONB, nullable=True)
    document_source_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=True)
    minute_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
