from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class NoteSource(Base):
    __tablename__ = "note_sources"

    note_id = Column(UUID(as_uuid=True), ForeignKey("notes.id", ondelete="CASCADE"), primary_key=True)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE"), primary_key=True)
    page_from = Column(Integer, nullable=True)
    page_to = Column(Integer, nullable=True)
