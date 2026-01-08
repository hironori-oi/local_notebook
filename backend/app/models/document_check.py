"""Document Check model for storing uploaded documents and check results."""

import uuid

from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer, String,
                        Text)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class DocumentCheck(Base):
    """
    Represents an uploaded document for checking.

    Each document can have multiple issues detected by the LLM.
    """

    __tablename__ = "document_checks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename = Column(String(255), nullable=False)
    file_type = Column(String(10), nullable=False)  # pdf, pptx
    original_text = Column(Text, nullable=False)  # Extracted text from document
    page_count = Column(Integer, nullable=True)  # Number of pages/slides
    status = Column(
        String(20), default="pending"
    )  # pending, processing, completed, failed
    error_message = Column(Text, nullable=True)
    check_types = Column(
        JSONB, nullable=False, default=list
    )  # List of enabled check types
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user = relationship("User", backref="document_checks")
    issues = relationship(
        "DocumentCheckIssue",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentCheckIssue.created_at",
    )


class DocumentCheckIssue(Base):
    """
    Represents an issue detected in the document.

    Issues include typos, grammar errors, expression improvements, etc.
    """

    __tablename__ = "document_check_issues"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("document_checks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category = Column(
        String(50), nullable=False
    )  # typo, grammar, expression, consistency, terminology, honorific, readability
    severity = Column(String(20), default="warning")  # error, warning, info
    page_or_slide = Column(Integer, nullable=True)  # Page or slide number
    line_number = Column(Integer, nullable=True)
    original_text = Column(Text, nullable=False)  # Text with the issue
    suggested_text = Column(Text, nullable=True)  # Suggested correction
    explanation = Column(Text, nullable=True)  # Why this is an issue
    is_accepted = Column(
        Boolean, nullable=True
    )  # User decision: True=accept, False=reject, None=pending
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    document = relationship("DocumentCheck", back_populates="issues")


class UserCheckPreference(Base):
    """
    User's default settings for document checking.

    Stores default check types and custom terminology dictionary.
    """

    __tablename__ = "user_check_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    default_check_types = Column(
        JSONB, nullable=False, default=list
    )  # Default enabled check types
    custom_terminology = Column(
        JSONB, nullable=True
    )  # Custom terminology dictionary {"term": "correct_form"}
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user = relationship("User", backref="check_preferences")
