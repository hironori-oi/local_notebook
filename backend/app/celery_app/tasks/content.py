"""
Celery tasks for content processing (sources and minutes).

This module provides tasks for:
- Processing source documents (chunking, embedding, formatting, summary)
- Processing minutes (formatting, summary generation)
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
    name="app.celery_app.tasks.content.process_source",
    queue="content",
    autoretry_for=RETRYABLE_EXCEPTIONS,
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,
    time_limit=600,
    soft_time_limit=540,
)
def process_source_task(self, source_id: str, raw_text: str):
    """
    Process source content: chunking, embedding generation, formatting, summary.

    Args:
        source_id: Source UUID string
        raw_text: Raw text extracted from document
    """
    from app.models.source import Source
    from app.services.content_processor import process_source_content

    logger.info(f"Processing source content: {source_id}")
    db = self.db

    try:
        source = db.query(Source).filter(Source.id == UUID(source_id)).first()
        if not source:
            logger.error(f"Source not found: {source_id}")
            return {"status": "error", "message": "Source not found"}

        # Run async processing in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                process_source_content(db, UUID(source_id), raw_text)
            )
        finally:
            loop.close()

        logger.info(f"Source content processed: {source_id}")
        return {"status": "completed", "source_id": source_id}

    except RETRYABLE_EXCEPTIONS as e:
        logger.warning(
            f"Retryable error for source {source_id}: {e}, "
            f"attempt {self.request.retries + 1}/{3 + 1}"
        )
        raise

    except Exception as e:
        logger.error(f"Source processing failed: {e}", exc_info=True)
        _mark_source_failed(db, source_id, str(e))
        return {"status": "failed", "message": str(e)}


@shared_task(
    bind=True,
    base=DatabaseTask,
    name="app.celery_app.tasks.content.process_minute",
    queue="content",
    autoretry_for=RETRYABLE_EXCEPTIONS,
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,
    time_limit=600,
    soft_time_limit=540,
)
def process_minute_task(self, minute_id: str):
    """
    Process minute content: formatting, summary generation.

    Args:
        minute_id: Minute UUID string
    """
    from app.models.minute import Minute
    from app.services.content_processor import process_minute_content

    logger.info(f"Processing minute content: {minute_id}")
    db = self.db

    try:
        minute = db.query(Minute).filter(Minute.id == UUID(minute_id)).first()
        if not minute:
            logger.error(f"Minute not found: {minute_id}")
            return {"status": "error", "message": "Minute not found"}

        # Run async processing in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(process_minute_content(db, UUID(minute_id)))
        finally:
            loop.close()

        logger.info(f"Minute content processed: {minute_id}")
        return {"status": "completed", "minute_id": minute_id}

    except RETRYABLE_EXCEPTIONS as e:
        logger.warning(
            f"Retryable error for minute {minute_id}: {e}, "
            f"attempt {self.request.retries + 1}/{3 + 1}"
        )
        raise

    except Exception as e:
        logger.error(f"Minute processing failed: {e}", exc_info=True)
        _mark_minute_failed(db, minute_id, str(e))
        return {"status": "failed", "message": str(e)}


def _mark_source_failed(db, source_id: str, error_message: str):
    """Mark a source as failed in the database."""
    from app.models.source import Source

    try:
        source = db.query(Source).filter(Source.id == UUID(source_id)).first()
        if source:
            source.processing_status = "failed"
            source.processing_error = error_message
            db.commit()
    except Exception as e:
        logger.error(f"Failed to update source error status: {e}")


def _mark_minute_failed(db, minute_id: str, error_message: str):
    """Mark a minute as failed in the database."""
    from app.models.minute import Minute

    try:
        minute = db.query(Minute).filter(Minute.id == UUID(minute_id)).first()
        if minute:
            minute.processing_status = "failed"
            minute.processing_error = error_message
            db.commit()
    except Exception as e:
        logger.error(f"Failed to update minute error status: {e}")


def enqueue_source_processing(source_id: UUID, raw_text: str) -> str:
    """
    Enqueue source content processing task.

    Args:
        source_id: Source UUID
        raw_text: Raw text extracted from document

    Returns:
        Celery task ID
    """
    result = process_source_task.delay(str(source_id), raw_text)
    logger.info(f"Enqueued source processing: {source_id}, celery_task_id: {result.id}")
    return result.id


def enqueue_minute_processing(minute_id: UUID) -> str:
    """
    Enqueue minute content processing task.

    Args:
        minute_id: Minute UUID

    Returns:
        Celery task ID
    """
    result = process_minute_task.delay(str(minute_id))
    logger.info(f"Enqueued minute processing: {minute_id}, celery_task_id: {result.id}")
    return result.id
