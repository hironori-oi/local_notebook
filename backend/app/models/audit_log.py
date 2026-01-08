"""
Audit Log model for tracking user actions.
"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action = Column(
        String, nullable=False
    )  # e.g., "login", "create_notebook", "upload_source"
    target_type = Column(String, nullable=True)  # e.g., "notebook", "source", "note"
    target_id = Column(String, nullable=True)  # ID of the affected resource
    details = Column(String, nullable=True)  # JSON-encoded additional details
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
