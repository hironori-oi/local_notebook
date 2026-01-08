"""
Celery tasks for slide generation.

This module provides tasks for:
- Generating PowerPoint slides from source text
- Refining slides based on user instructions
"""

import logging
import asyncio
from uuid import UUID

from celery import shared_task

from app.celery_app.tasks.base import DatabaseTask
from app.celery_app.config import RETRY_CONFIG, RETRYABLE_EXCEPTIONS

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    base=DatabaseTask,
    name="app.celery_app.tasks.slide.process_slide_generation",
    queue="llm",
    autoretry_for=RETRYABLE_EXCEPTIONS,
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,
    time_limit=600,
    soft_time_limit=540,
)
def process_slide_generation_task(self, project_id: str):
    """
    Process slide generation for a project.

    Args:
        project_id: Slide project UUID string
    """
    from app.models.slide_project import SlideProject
    from app.services.slide_generator import process_slide_generation

    logger.info(f"Processing slide generation: {project_id}")
    db = self.db

    try:
        project = db.query(SlideProject).filter(
            SlideProject.id == UUID(project_id)
        ).first()
        if not project:
            logger.error(f"Slide project not found: {project_id}")
            return {"status": "error", "message": "Slide project not found"}

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                process_slide_generation(db, UUID(project_id))
            )
        finally:
            loop.close()

        logger.info(f"Slide generation processed: {project_id}")
        return {"status": "completed", "project_id": project_id}

    except RETRYABLE_EXCEPTIONS as e:
        logger.warning(
            f"Retryable error for slide project {project_id}: {e}, "
            f"attempt {self.request.retries + 1}/{3 + 1}"
        )
        raise

    except Exception as e:
        logger.error(f"Slide generation failed: {e}", exc_info=True)
        _mark_project_failed(db, project_id, str(e))
        return {"status": "failed", "message": str(e)}


def _mark_project_failed(db, project_id: str, error_message: str):
    """Mark a slide project as failed in the database."""
    from app.models.slide_project import SlideProject

    try:
        project = db.query(SlideProject).filter(
            SlideProject.id == UUID(project_id)
        ).first()
        if project:
            project.status = "failed"
            project.error_message = error_message
            db.commit()
    except Exception as e:
        logger.error(f"Failed to update slide project error status: {e}")


def enqueue_slide_generation(project_id: UUID) -> str:
    """
    Enqueue slide generation processing task.

    Args:
        project_id: Slide project UUID

    Returns:
        Celery task ID
    """
    result = process_slide_generation_task.delay(str(project_id))
    logger.info(f"Enqueued slide generation: {project_id}, celery_task_id: {result.id}")
    return result.id
