"""
Celery tasks for council-related processing.

This module provides tasks for:
- Processing council agenda content (materials and minutes)
- Regenerating agenda summaries
"""

import asyncio
import logging
from typing import Literal
from uuid import UUID

from celery import shared_task

from app.celery_app.config import RETRY_CONFIG, RETRYABLE_EXCEPTIONS
from app.celery_app.tasks.base import DatabaseTask

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    base=DatabaseTask,
    name="app.celery_app.tasks.council.process_agenda_content",
    queue="content",
    autoretry_for=RETRYABLE_EXCEPTIONS,
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,
    time_limit=600,
    soft_time_limit=540,
)
def process_agenda_content_task(self, agenda_id: str):
    """
    Process council agenda content (both materials and minutes).

    Args:
        agenda_id: Agenda item UUID string
    """
    from app.models.council_agenda_item import CouncilAgendaItem
    from app.services.council_content_processor import process_agenda_content

    logger.info(f"Processing agenda content: {agenda_id}")
    db = self.db

    try:
        agenda = (
            db.query(CouncilAgendaItem)
            .filter(CouncilAgendaItem.id == UUID(agenda_id))
            .first()
        )
        if not agenda:
            logger.error(f"Agenda item not found: {agenda_id}")
            return {"status": "error", "message": "Agenda item not found"}

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(process_agenda_content(db, UUID(agenda_id)))
        finally:
            loop.close()

        logger.info(f"Agenda content processed: {agenda_id}")
        return {"status": "completed", "agenda_id": agenda_id}

    except RETRYABLE_EXCEPTIONS as e:
        logger.warning(f"Retryable error for agenda {agenda_id}: {e}")
        raise

    except Exception as e:
        logger.error(f"Agenda processing failed: {e}", exc_info=True)
        _mark_agenda_failed(db, agenda_id, str(e))
        return {"status": "failed", "message": str(e)}


@shared_task(
    bind=True,
    base=DatabaseTask,
    name="app.celery_app.tasks.council.process_agenda_materials",
    queue="content",
    autoretry_for=RETRYABLE_EXCEPTIONS,
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,
    time_limit=600,
    soft_time_limit=540,
)
def process_agenda_materials_task(self, agenda_id: str):
    """
    Process only the materials portion of a council agenda item.

    Args:
        agenda_id: Agenda item UUID string
    """
    from app.models.council_agenda_item import CouncilAgendaItem
    from app.services.council_content_processor import process_agenda_materials

    logger.info(f"Processing agenda materials: {agenda_id}")
    db = self.db

    try:
        agenda = (
            db.query(CouncilAgendaItem)
            .filter(CouncilAgendaItem.id == UUID(agenda_id))
            .first()
        )
        if not agenda:
            logger.error(f"Agenda item not found: {agenda_id}")
            return {"status": "error", "message": "Agenda item not found"}

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(process_agenda_materials(db, UUID(agenda_id)))
        finally:
            loop.close()

        logger.info(f"Agenda materials processed: {agenda_id}")
        return {"status": "completed", "agenda_id": agenda_id}

    except RETRYABLE_EXCEPTIONS as e:
        logger.warning(f"Retryable error for agenda materials {agenda_id}: {e}")
        raise

    except Exception as e:
        logger.error(f"Agenda materials processing failed: {e}", exc_info=True)
        _mark_agenda_failed(db, agenda_id, str(e), "materials")
        return {"status": "failed", "message": str(e)}


@shared_task(
    bind=True,
    base=DatabaseTask,
    name="app.celery_app.tasks.council.process_agenda_minutes",
    queue="content",
    autoretry_for=RETRYABLE_EXCEPTIONS,
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,
    time_limit=600,
    soft_time_limit=540,
)
def process_agenda_minutes_task(self, agenda_id: str):
    """
    Process only the minutes portion of a council agenda item.

    Args:
        agenda_id: Agenda item UUID string
    """
    from app.models.council_agenda_item import CouncilAgendaItem
    from app.services.council_content_processor import process_agenda_minutes

    logger.info(f"Processing agenda minutes: {agenda_id}")
    db = self.db

    try:
        agenda = (
            db.query(CouncilAgendaItem)
            .filter(CouncilAgendaItem.id == UUID(agenda_id))
            .first()
        )
        if not agenda:
            logger.error(f"Agenda item not found: {agenda_id}")
            return {"status": "error", "message": "Agenda item not found"}

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(process_agenda_minutes(db, UUID(agenda_id)))
        finally:
            loop.close()

        logger.info(f"Agenda minutes processed: {agenda_id}")
        return {"status": "completed", "agenda_id": agenda_id}

    except RETRYABLE_EXCEPTIONS as e:
        logger.warning(f"Retryable error for agenda minutes {agenda_id}: {e}")
        raise

    except Exception as e:
        logger.error(f"Agenda minutes processing failed: {e}", exc_info=True)
        _mark_agenda_failed(db, agenda_id, str(e), "minutes")
        return {"status": "failed", "message": str(e)}


@shared_task(
    bind=True,
    base=DatabaseTask,
    name="app.celery_app.tasks.council.regenerate_agenda_summary",
    queue="content",
    autoretry_for=RETRYABLE_EXCEPTIONS,
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=300,
    time_limit=300,
    soft_time_limit=270,
)
def regenerate_agenda_summary_task(
    self,
    agenda_id: str,
    content_type: str = "both",
):
    """
    Regenerate summary for an agenda item.

    Args:
        agenda_id: Agenda item UUID string
        content_type: "materials", "minutes", or "both"
    """
    from app.models.council_agenda_item import CouncilAgendaItem
    from app.services.council_content_processor import \
        regenerate_agenda_summary

    logger.info(f"Regenerating agenda summary: {agenda_id}, type: {content_type}")
    db = self.db

    try:
        agenda = (
            db.query(CouncilAgendaItem)
            .filter(CouncilAgendaItem.id == UUID(agenda_id))
            .first()
        )
        if not agenda:
            logger.error(f"Agenda item not found: {agenda_id}")
            return {"status": "error", "message": "Agenda item not found"}

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                regenerate_agenda_summary(
                    db,
                    UUID(agenda_id),
                    content_type,  # type: ignore
                )
            )
        finally:
            loop.close()

        logger.info(f"Agenda summary regenerated: {agenda_id}")
        return {"status": "completed", "agenda_id": agenda_id}

    except RETRYABLE_EXCEPTIONS as e:
        logger.warning(f"Retryable error for agenda summary {agenda_id}: {e}")
        raise

    except Exception as e:
        logger.error(f"Agenda summary regeneration failed: {e}", exc_info=True)
        return {"status": "failed", "message": str(e)}


def _mark_agenda_failed(
    db,
    agenda_id: str,
    error_message: str,
    content_type: str = "both",
):
    """Mark an agenda item's processing as failed."""
    from app.models.council_agenda_item import CouncilAgendaItem

    try:
        agenda = (
            db.query(CouncilAgendaItem)
            .filter(CouncilAgendaItem.id == UUID(agenda_id))
            .first()
        )
        if agenda:
            if content_type in ("both", "materials"):
                agenda.materials_processing_status = "failed"
                agenda.materials_processing_error = error_message
            if content_type in ("both", "minutes"):
                agenda.minutes_processing_status = "failed"
                agenda.minutes_processing_error = error_message
            db.commit()
    except Exception as e:
        logger.error(f"Failed to update agenda error status: {e}")


def enqueue_agenda_content_processing(agenda_id: UUID) -> str:
    """Enqueue agenda content processing task."""
    result = process_agenda_content_task.delay(str(agenda_id))
    logger.info(f"Enqueued agenda processing: {agenda_id}, celery_task_id: {result.id}")
    return result.id


def enqueue_agenda_materials_processing(agenda_id: UUID) -> str:
    """Enqueue agenda materials processing task."""
    result = process_agenda_materials_task.delay(str(agenda_id))
    logger.info(
        f"Enqueued agenda materials processing: {agenda_id}, celery_task_id: {result.id}"
    )
    return result.id


def enqueue_agenda_minutes_processing(agenda_id: UUID) -> str:
    """Enqueue agenda minutes processing task."""
    result = process_agenda_minutes_task.delay(str(agenda_id))
    logger.info(
        f"Enqueued agenda minutes processing: {agenda_id}, celery_task_id: {result.id}"
    )
    return result.id


def enqueue_agenda_summary_regeneration(
    agenda_id: UUID,
    content_type: Literal["materials", "minutes", "both"] = "both",
) -> str:
    """Enqueue agenda summary regeneration task."""
    result = regenerate_agenda_summary_task.delay(str(agenda_id), content_type)
    logger.info(
        f"Enqueued agenda summary regeneration: {agenda_id}, celery_task_id: {result.id}"
    )
    return result.id
