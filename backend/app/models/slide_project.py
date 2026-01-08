"""Slide Generator models for PowerPoint generation."""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class SlideProject(Base):
    """
    Represents a slide generation project.

    Each project contains source text and generated slides.
    """

    __tablename__ = "slide_projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=False)
    source_text = Column(Text, nullable=False)  # Input text
    target_slide_count = Column(Integer, nullable=True)  # Target number of slides
    key_points = Column(Text, nullable=True)  # Key points to emphasize
    template_id = Column(
        UUID(as_uuid=True),
        ForeignKey("slide_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    style_id = Column(
        UUID(as_uuid=True),
        ForeignKey("slide_styles.id", ondelete="SET NULL"),
        nullable=True,
    )
    status = Column(String(20), default="draft")  # draft, generating, completed, failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user = relationship("User", backref="slide_projects")
    template = relationship("SlideTemplate", back_populates="projects")
    style = relationship("SlideStyle", back_populates="projects")
    slides = relationship(
        "SlideContent",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="SlideContent.slide_number",
    )
    messages = relationship(
        "SlideMessage",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="SlideMessage.created_at",
    )


class SlideContent(Base):
    """
    Represents individual slide content.

    Each slide has a title, content (bullets, details), and speaker notes.
    """

    __tablename__ = "slide_contents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("slide_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slide_number = Column(Integer, nullable=False)
    slide_type = Column(
        String(50), default="content"
    )  # title, content, section, conclusion
    title = Column(String(500), nullable=False)
    content = Column(JSONB, nullable=False, default=dict)
    # content structure:
    # {
    #   "subtitle": "optional subtitle for title slides",
    #   "bullets": ["point 1", "point 2"],
    #   "details": "optional detailed text"
    # }
    speaker_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    project = relationship("SlideProject", back_populates="slides")


class SlideMessage(Base):
    """
    Chat history for slide refinement.

    Stores user instructions and assistant responses.
    """

    __tablename__ = "slide_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("slide_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(20), nullable=False)  # user, assistant
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    project = relationship("SlideProject", back_populates="messages")


class SlideTemplate(Base):
    """
    User-uploaded PowerPoint template files.

    Templates are .pptx files used as base for generated slides.
    """

    __tablename__ = "slide_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    file_path = Column(String(500), nullable=False)  # Path to saved pptx file
    original_filename = Column(String(255), nullable=False)
    slide_count = Column(Integer, nullable=False)  # Number of slides in template
    layout_info = Column(JSONB, nullable=True)  # Parsed layout information
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", backref="slide_templates")
    projects = relationship("SlideProject", back_populates="template")


class SlideStyle(Base):
    """
    User-defined style settings.

    Styles define colors, fonts, and layout preferences.
    """

    __tablename__ = "slide_styles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    settings = Column(JSONB, nullable=False, default=dict)
    # settings structure:
    # {
    #   "colors": {
    #     "primary": "#1a73e8",
    #     "secondary": "#5f6368",
    #     "accent": "#ea4335",
    #     "background": "#ffffff",
    #     "text": "#202124"
    #   },
    #   "fonts": {
    #     "title": "Yu Gothic",
    #     "body": "Meiryo"
    #   },
    #   "sizes": {
    #     "title": 44,
    #     "subtitle": 32,
    #     "body": 24,
    #     "caption": 18
    #   },
    #   "layout_preference": "modern"  # modern, classic, minimal
    # }
    is_default = Column(Integer, default=0)  # 1 if this is user's default style
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user = relationship("User", backref="slide_styles")
    projects = relationship("SlideProject", back_populates="style")
