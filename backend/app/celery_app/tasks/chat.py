"""
Celery tasks for chat processing.

This module provides tasks for:
- Processing chat messages with RAG retrieval and LLM response
"""

import asyncio
import logging
from typing import List, Optional
from uuid import UUID

from celery import shared_task

from app.celery_app.config import RETRYABLE_EXCEPTIONS
from app.celery_app.tasks.base import DatabaseTask

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    base=DatabaseTask,
    name="app.celery_app.tasks.chat.process_message",
    queue="chat",
    max_retries=1,  # Chat needs fast failure, minimal retries
    time_limit=120,
    soft_time_limit=100,
)
def process_chat_message_task(
    self,
    message_id: str,
    notebook_id: str,
    session_id: Optional[str],
    question: str,
    source_ids: Optional[List[str]],
    use_rag: bool,
    use_formatted_text: bool,
):
    """
    Process chat message with RAG retrieval and LLM response.

    Args:
        message_id: Message UUID string
        notebook_id: Notebook UUID string
        session_id: Optional session UUID string
        question: User's question
        source_ids: Optional list of source IDs to search
        use_rag: Whether to use RAG retrieval
        use_formatted_text: Whether to use formatted source text
    """
    from app.core.config import settings
    from app.services.chat_processor import process_chat_message_async

    logger.info(f"Processing chat message: {message_id}")
    db = self.db

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                process_chat_message_async(
                    message_id=UUID(message_id),
                    db_url=settings.DATABASE_URL,
                    notebook_id=UUID(notebook_id),
                    session_id=UUID(session_id) if session_id else None,
                    question=question,
                    source_ids=source_ids,
                    use_rag=use_rag,
                    use_formatted_text=use_formatted_text,
                )
            )
        finally:
            loop.close()

        logger.info(f"Chat message processed: {message_id}")
        return {"status": "completed", "message_id": message_id}

    except Exception as e:
        logger.error(f"Chat processing failed: {e}", exc_info=True)
        _mark_message_failed(db, message_id, str(e))
        return {"status": "failed", "message": str(e)}


def _mark_message_failed(db, message_id: str, error_message: str):
    """Mark a chat message as failed in the database."""
    from app.models.chat import ChatMessage

    try:
        message = (
            db.query(ChatMessage).filter(ChatMessage.id == UUID(message_id)).first()
        )
        if message:
            message.status = "failed"
            message.error_message = error_message
            db.commit()
    except Exception as e:
        logger.error(f"Failed to update message error status: {e}")


def enqueue_chat_processing(
    message_id: UUID,
    notebook_id: UUID,
    session_id: Optional[UUID],
    question: str,
    source_ids: Optional[List[str]],
    use_rag: bool,
    use_formatted_text: bool,
) -> str:
    """
    Enqueue chat message processing task.

    Args:
        message_id: Message UUID
        notebook_id: Notebook UUID
        session_id: Optional session UUID
        question: User's question
        source_ids: Optional list of source IDs
        use_rag: Whether to use RAG
        use_formatted_text: Whether to use formatted text

    Returns:
        Celery task ID
    """
    result = process_chat_message_task.delay(
        str(message_id),
        str(notebook_id),
        str(session_id) if session_id else None,
        question,
        source_ids,
        use_rag,
        use_formatted_text,
    )
    logger.info(f"Enqueued chat processing: {message_id}, celery_task_id: {result.id}")
    return result.id
