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
from app.core.exceptions import BadRequestError, EmbeddingError

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
