"""CouncilAgendaChunk model for RAG vector search."""
import uuid
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.db.base import Base
from app.core.config import settings


class CouncilAgendaChunk(Base):
    """
    Represents a text chunk from council agenda item content for RAG.

    Each chunk contains a portion of either materials or minutes text,
    along with its embedding vector for similarity search.
    """
    __tablename__ = "council_agenda_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agenda_id = Column(
        UUID(as_uuid=True),
        ForeignKey("council_agenda_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # For materials chunks, links to specific material
    material_id = Column(
        UUID(as_uuid=True),
        ForeignKey("council_agenda_materials.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    chunk_type = Column(String(20), nullable=False)  # "materials" or "minutes"
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(dim=settings.EMBEDDING_DIM), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    agenda = relationship("CouncilAgendaItem", back_populates="chunks")
    material = relationship("CouncilAgendaMaterial", back_populates="chunks")
