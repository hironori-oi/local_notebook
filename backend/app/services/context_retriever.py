"""
Context Retriever service for extracting RAG context without saving messages.

This module provides context retrieval functionality that can be used by
infographic and slide generation services without the side effects of
message storage that occur in the main RAG flow.
"""
import logging
from dataclasses import dataclass
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import select, text, func, bindparam
from sqlalchemy.types import String

from app.services.embedding import embed_texts
from app.models.source import Source
from app.models.minute import Minute
from app.models.council_agenda_item import CouncilAgendaItem
from app.models.council_meeting import CouncilMeeting
from app.core.exceptions import BadRequestError, EmbeddingError
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ContextResult:
    """Result of context retrieval containing document chunks and references."""
    contexts: List[str]  # Retrieved text chunks
    source_refs: List[str]  # Source references ("Title(p.X)" format)


async def retrieve_context(
    db: Session,
    notebook_id: UUID,
    source_ids: Optional[List[UUID]],
    query: str,
    user_id: UUID,
    top_k: int = 8,
) -> ContextResult:
    """
    Retrieve relevant document chunks for a query without saving messages.

    This extracts the core retrieval logic from rag_answer() without the
    message-saving side effects, making it suitable for content generation
    tasks like infographic and slide creation.

    Args:
        db: Database session
        notebook_id: Target notebook UUID
        source_ids: Optional list of source UUIDs to search. If None, all sources
                   in the notebook are searched.
        query: The query text to search for relevant context
        user_id: User ID for permission validation
        top_k: Maximum number of chunks to retrieve (default: 8)

    Returns:
        ContextResult with contexts and source_refs

    Raises:
        BadRequestError: If source_ids don't belong to the notebook
        EmbeddingError: If embedding generation fails
    """
    # 1. Get target source IDs with ownership validation
    if source_ids:
        # SECURITY: Validate all source_ids belong to the specified notebook
        valid_count = db.execute(
            select(func.count(Source.id)).where(
                Source.id.in_(source_ids),
                Source.notebook_id == notebook_id
            )
        ).scalar()

        if valid_count != len(source_ids):
            logger.warning(
                f"User {user_id} attempted to access sources not belonging to notebook {notebook_id}"
            )
            raise BadRequestError(
                "指定されたソースIDの一部がこのノートブックに存在しません"
            )
        target_source_ids = source_ids
    else:
        # Get all sources in the notebook
        rows = db.execute(
            select(Source.id).where(Source.notebook_id == notebook_id)
        )
        target_source_ids = [row[0] for row in rows]

    if not target_source_ids:
        logger.info(f"No sources found in notebook {notebook_id}")
        return ContextResult(contexts=[], source_refs=[])

    # 2. Generate query embedding
    try:
        [q_emb] = await embed_texts([query])
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise EmbeddingError(f"埋め込み生成に失敗しました: {str(e)}")

    # 3. Similarity search with pgvector
    # Convert embedding list to pgvector string format '[1.0, 2.0, ...]'
    q_emb_str = "[" + ",".join(str(x) for x in q_emb) + "]"

    # Use CAST syntax to avoid SQLAlchemy misinterpreting ::vector
    sql = text(
        """
        SELECT sc.id, sc.content, sc.page_number, s.title
        FROM source_chunks sc
        JOIN sources s ON sc.source_id = s.id
        WHERE sc.source_id = ANY(:source_ids)
        ORDER BY sc.embedding <-> CAST(:query_emb AS vector)
        LIMIT :limit
        """
    ).bindparams(bindparam("query_emb", type_=String))

    try:
        rows = db.execute(
            sql,
            {
                "source_ids": target_source_ids,
                "query_emb": q_emb_str,
                "limit": top_k,
            },
        ).fetchall()
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        raise BadRequestError(f"類似検索に失敗しました: {str(e)}")

    # 4. Build context and source references
    contexts: List[str] = []
    source_refs: List[str] = []

    for _id, content, page_number, title in rows:
        contexts.append(content)
        ref = f"{title}"
        if page_number:
            ref += f"(p.{page_number})"
        source_refs.append(ref)

    logger.debug(f"Retrieved {len(contexts)} context chunks for query")
    return ContextResult(contexts=contexts, source_refs=source_refs)


def format_context_for_prompt(context_result: ContextResult) -> str:
    """
    Format retrieved contexts into a single string for LLM prompts.

    Args:
        context_result: ContextResult from retrieve_context()

    Returns:
        Formatted string with context chunks separated by dividers
    """
    if not context_result.contexts:
        return ""
    return "\n\n---\n\n".join(context_result.contexts)


async def retrieve_minute_context(
    db: Session,
    notebook_id: UUID,
    minute_ids: List[UUID],
    query: str,
    user_id: UUID,
    top_k: int = 10,
) -> ContextResult:
    """
    Retrieve relevant chunks from minute records.

    Args:
        db: Database session
        notebook_id: Target notebook UUID
        minute_ids: List of minute UUIDs to search
        query: The query text to search for relevant context
        user_id: User ID for permission validation
        top_k: Maximum number of chunks to retrieve (default: 10)

    Returns:
        ContextResult with contexts and source_refs

    Raises:
        BadRequestError: If minute_ids don't belong to the notebook
        EmbeddingError: If embedding generation fails
    """
    if not minute_ids:
        return ContextResult(contexts=[], source_refs=[])

    # 1. Validate minute_ids belong to the notebook
    valid_count = db.execute(
        select(func.count(Minute.id)).where(
            Minute.id.in_(minute_ids),
            Minute.notebook_id == notebook_id
        )
    ).scalar()

    if valid_count != len(minute_ids):
        logger.warning(
            f"User {user_id} attempted to access minutes not belonging to notebook {notebook_id}"
        )
        raise BadRequestError(
            "指定された議事録IDの一部がこのノートブックに存在しません"
        )

    # 2. Generate query embedding
    try:
        [q_emb] = await embed_texts([query])
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise EmbeddingError(f"埋め込み生成に失敗しました: {str(e)}")

    # 3. Similarity search with pgvector on minute_chunks
    q_emb_str = "[" + ",".join(str(x) for x in q_emb) + "]"

    sql = text(
        """
        SELECT mc.id, mc.content, m.title
        FROM minute_chunks mc
        JOIN minutes m ON mc.minute_id = m.id
        WHERE mc.minute_id = ANY(:minute_ids)
        ORDER BY mc.embedding <-> CAST(:query_emb AS vector)
        LIMIT :limit
        """
    ).bindparams(bindparam("query_emb", type_=String))

    try:
        rows = db.execute(
            sql,
            {
                "minute_ids": minute_ids,
                "query_emb": q_emb_str,
                "limit": top_k,
            },
        ).fetchall()
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        raise BadRequestError(f"類似検索に失敗しました: {str(e)}")

    # 4. Build context and source references
    contexts: List[str] = []
    source_refs: List[str] = []

    for _id, content, title in rows:
        contexts.append(content)
        source_refs.append(f"議事録: {title}")

    logger.debug(f"Retrieved {len(contexts)} context chunks from minutes")
    return ContextResult(contexts=contexts, source_refs=source_refs)


@dataclass
class SummaryResult:
    """Result of summary retrieval for email generation."""
    document_summaries: List[str]  # Summaries from sources
    document_refs: List[str]  # Source references
    minute_summaries: List[str]  # Summaries from minutes
    minute_refs: List[str]  # Minute references
    pending_sources: List[str]  # Sources still being processed
    pending_minutes: List[str]  # Minutes still being processed


async def retrieve_summaries_for_email(
    db: Session,
    notebook_id: UUID,
    source_ids: Optional[List[UUID]],
    minute_ids: Optional[List[UUID]],
    user_id: UUID,
) -> SummaryResult:
    """
    Retrieve pre-generated summaries for email generation.

    This function fetches summaries (or fallback content) from sources and minutes
    for use in email generation. Unlike chunk-based retrieval, this uses the
    full pre-generated summaries to preserve all information.

    Fallback order:
    - Sources: summary -> formatted_text -> full_text (first 3000 chars)
    - Minutes: summary -> formatted_content -> content (first 3000 chars)

    Args:
        db: Database session
        notebook_id: Target notebook UUID
        source_ids: Optional list of source UUIDs
        minute_ids: Optional list of minute UUIDs
        user_id: User ID for permission validation

    Returns:
        SummaryResult with document and minute summaries

    Raises:
        BadRequestError: If source_ids or minute_ids don't belong to the notebook
    """
    document_summaries: List[str] = []
    document_refs: List[str] = []
    minute_summaries: List[str] = []
    minute_refs: List[str] = []
    pending_sources: List[str] = []
    pending_minutes: List[str] = []

    MAX_FALLBACK_LENGTH = settings.CONTENT_FALLBACK_MAX_LENGTH

    # 1. Get source summaries
    if source_ids:
        # Validate source_ids belong to the notebook
        sources = db.query(Source).filter(
            Source.id.in_(source_ids),
            Source.notebook_id == notebook_id
        ).all()

        if len(sources) != len(source_ids):
            logger.warning(
                f"User {user_id} attempted to access sources not belonging to notebook {notebook_id}"
            )
            raise BadRequestError(
                "指定されたソースIDの一部がこのノートブックに存在しません"
            )

        for source in sources:
            # Check processing status
            if source.processing_status in ("pending", "processing"):
                pending_sources.append(source.title)
                logger.info(f"Source {source.id} is still being processed")

            # Get summary with fallback
            summary_text = None
            if source.summary and source.summary.strip():
                summary_text = source.summary
            elif source.formatted_text and source.formatted_text.strip():
                summary_text = source.formatted_text[:MAX_FALLBACK_LENGTH]
                if len(source.formatted_text) > MAX_FALLBACK_LENGTH:
                    summary_text += "..."
                logger.debug(f"Using formatted_text fallback for source {source.id}")
            elif source.full_text and source.full_text.strip():
                summary_text = source.full_text[:MAX_FALLBACK_LENGTH]
                if len(source.full_text) > MAX_FALLBACK_LENGTH:
                    summary_text += "..."
                logger.debug(f"Using full_text fallback for source {source.id}")

            if summary_text:
                document_summaries.append(summary_text)
                document_refs.append(source.title)

    # 2. Get minute summaries
    if minute_ids:
        # Validate minute_ids belong to the notebook
        minutes = db.query(Minute).filter(
            Minute.id.in_(minute_ids),
            Minute.notebook_id == notebook_id
        ).all()

        if len(minutes) != len(minute_ids):
            logger.warning(
                f"User {user_id} attempted to access minutes not belonging to notebook {notebook_id}"
            )
            raise BadRequestError(
                "指定された議事録IDの一部がこのノートブックに存在しません"
            )

        for minute in minutes:
            # Check processing status
            if minute.processing_status in ("pending", "processing"):
                pending_minutes.append(minute.title)
                logger.info(f"Minute {minute.id} is still being processed")

            # Get summary with fallback
            summary_text = None
            if minute.summary and minute.summary.strip():
                summary_text = minute.summary
            elif minute.formatted_content and minute.formatted_content.strip():
                summary_text = minute.formatted_content[:MAX_FALLBACK_LENGTH]
                if len(minute.formatted_content) > MAX_FALLBACK_LENGTH:
                    summary_text += "..."
                logger.debug(f"Using formatted_content fallback for minute {minute.id}")
            elif minute.content and minute.content.strip():
                summary_text = minute.content[:MAX_FALLBACK_LENGTH]
                if len(minute.content) > MAX_FALLBACK_LENGTH:
                    summary_text += "..."
                logger.debug(f"Using raw content fallback for minute {minute.id}")

            if summary_text:
                minute_summaries.append(summary_text)
                minute_refs.append(f"議事録: {minute.title}")

    logger.info(
        f"Retrieved summaries: {len(document_summaries)} documents, {len(minute_summaries)} minutes, "
        f"{len(pending_sources)} pending sources, {len(pending_minutes)} pending minutes"
    )

    return SummaryResult(
        document_summaries=document_summaries,
        document_refs=document_refs,
        minute_summaries=minute_summaries,
        minute_refs=minute_refs,
        pending_sources=pending_sources,
        pending_minutes=pending_minutes,
    )


def format_summaries_for_prompt(summary_result: SummaryResult) -> tuple[str, str]:
    """
    Format retrieved summaries into strings for LLM prompts.

    Args:
        summary_result: SummaryResult from retrieve_summaries_for_email()

    Returns:
        Tuple of (document_context, minute_context) strings
    """
    # Format document summaries
    doc_parts = []
    for summary, ref in zip(summary_result.document_summaries, summary_result.document_refs):
        doc_parts.append(f"【{ref}】\n{summary}")
    document_context = "\n\n---\n\n".join(doc_parts) if doc_parts else ""

    # Format minute summaries
    minute_parts = []
    for summary, ref in zip(summary_result.minute_summaries, summary_result.minute_refs):
        minute_parts.append(f"【{ref}】\n{summary}")
    minute_context = "\n\n---\n\n".join(minute_parts) if minute_parts else ""

    return document_context, minute_context


# =============================================================================
# Council Context Retrieval
# =============================================================================

async def retrieve_council_context(
    db: Session,
    meeting_id: UUID,
    agenda_ids: Optional[List[UUID]],
    query: str,
    user_id: UUID,
    top_k: int = 10,
) -> ContextResult:
    """
    Retrieve relevant document chunks from council agenda items.

    This retrieves context from council_agenda_chunks for infographic generation.

    Args:
        db: Database session
        meeting_id: Target council meeting UUID
        agenda_ids: Optional list of agenda UUIDs to search. If None, all agendas
                   in the meeting are searched.
        query: The query text to search for relevant context
        user_id: User ID for permission validation
        top_k: Maximum number of chunks to retrieve (default: 10)

    Returns:
        ContextResult with contexts and source_refs

    Raises:
        BadRequestError: If agenda_ids don't belong to the meeting
        EmbeddingError: If embedding generation fails
    """
    # 1. Get target agenda IDs with validation
    if agenda_ids:
        # Validate all agenda_ids belong to the specified meeting
        valid_count = db.execute(
            select(func.count(CouncilAgendaItem.id)).where(
                CouncilAgendaItem.id.in_(agenda_ids),
                CouncilAgendaItem.meeting_id == meeting_id
            )
        ).scalar()

        if valid_count != len(agenda_ids):
            logger.warning(
                f"User {user_id} attempted to access agendas not belonging to meeting {meeting_id}"
            )
            raise BadRequestError(
                "指定された議題IDの一部がこの開催回に存在しません"
            )
        target_agenda_ids = agenda_ids
    else:
        # Get all agendas in the meeting that have been processed
        rows = db.execute(
            select(CouncilAgendaItem.id).where(
                CouncilAgendaItem.meeting_id == meeting_id,
                (
                    (CouncilAgendaItem.materials_processing_status == "completed") |
                    (CouncilAgendaItem.minutes_processing_status == "completed")
                )
            )
        )
        target_agenda_ids = [row[0] for row in rows]

    if not target_agenda_ids:
        logger.info(f"No processed agendas found in meeting {meeting_id}")
        return ContextResult(contexts=[], source_refs=[])

    # 2. Generate query embedding
    try:
        [q_emb] = await embed_texts([query])
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise EmbeddingError(f"埋め込み生成に失敗しました: {str(e)}")

    # 3. Similarity search with pgvector on council_agenda_chunks
    q_emb_str = "[" + ",".join(str(x) for x in q_emb) + "]"

    sql = text(
        """
        SELECT cac.id, cac.content, cac.chunk_type,
               cai.agenda_number, cai.title as agenda_title
        FROM council_agenda_chunks cac
        JOIN council_agenda_items cai ON cac.agenda_id = cai.id
        WHERE cac.agenda_id = ANY(:agenda_ids)
        ORDER BY cac.embedding <-> CAST(:query_emb AS vector)
        LIMIT :limit
        """
    ).bindparams(bindparam("query_emb", type_=String))

    try:
        rows = db.execute(
            sql,
            {
                "agenda_ids": target_agenda_ids,
                "query_emb": q_emb_str,
                "limit": top_k,
            },
        ).fetchall()
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        raise BadRequestError(f"類似検索に失敗しました: {str(e)}")

    # 4. Build context and source references
    contexts: List[str] = []
    source_refs: List[str] = []

    for _id, content, chunk_type, agenda_number, agenda_title in rows:
        contexts.append(content)
        type_label = "資料" if chunk_type == "materials" else "議事録"
        ref = f"議題{agenda_number}"
        if agenda_title:
            ref += f": {agenda_title}"
        ref += f" ({type_label})"
        source_refs.append(ref)

    logger.debug(f"Retrieved {len(contexts)} context chunks from council agendas")
    return ContextResult(contexts=contexts, source_refs=source_refs)
