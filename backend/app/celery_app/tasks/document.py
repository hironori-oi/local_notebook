"""
Celery tasks for document checking.

This module provides tasks for:
- Processing document checks (typos, grammar, expressions, etc.)
"""

import asyncio
import logging
from uuid import UUID

from celery import shared_task

from app.celery_app.config import RETRY_CONFIG, RETRYABLE_EXCEPTIONS
from app.celery_app.tasks.base import DatabaseTask

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    base=DatabaseTask,
    name="app.celery_app.tasks.document.process_document_check",
    queue="llm",
    autoretry_for=RETRYABLE_EXCEPTIONS,
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,
    time_limit=600,
    soft_time_limit=540,
)
def process_document_check_task(self, document_id: str):
    """
    Process document check: run LLM analysis and store results.

    Args:
        document_id: Document check UUID string
    """
    from app.models.document_check import DocumentCheck
    from app.services.document_checker import process_document_check

    logger.info(f"Processing document check: {document_id}")
    db = self.db

    try:
        document = (
            db.query(DocumentCheck)
            .filter(DocumentCheck.id == UUID(document_id))
            .first()
        )
        if not document:
            logger.error(f"Document check not found: {document_id}")
            return {"status": "error", "message": "Document check not found"}

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(process_document_check(db, UUID(document_id)))
        finally:
            loop.close()

        logger.info(f"Document check processed: {document_id}")
        return {"status": "completed", "document_id": document_id}

    except RETRYABLE_EXCEPTIONS as e:
        logger.warning(
            f"Retryable error for document {document_id}: {e}, "
            f"attempt {self.request.retries + 1}/{3 + 1}"
        )
        raise

    except Exception as e:
        logger.error(f"Document check failed: {e}", exc_info=True)
        _mark_document_failed(db, document_id, str(e))
        return {"status": "failed", "message": str(e)}


def _mark_document_failed(db, document_id: str, error_message: str):
    """Mark a document check as failed in the database."""
    from app.models.document_check import DocumentCheck

    try:
        document = (
            db.query(DocumentCheck)
            .filter(DocumentCheck.id == UUID(document_id))
            .first()
        )
        if document:
            document.status = "failed"
            document.error_message = error_message
            db.commit()
    except Exception as e:
        logger.error(f"Failed to update document error status: {e}")


def enqueue_document_check(document_id: UUID) -> str:
    """
    Enqueue document check processing task.

    Args:
        document_id: Document check UUID

    Returns:
        Celery task ID
    """
    result = process_document_check_task.delay(str(document_id))
    logger.info(f"Enqueued document check: {document_id}, celery_task_id: {result.id}")
    return result.id
