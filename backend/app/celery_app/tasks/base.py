"""
Base task classes and utilities for Celery tasks.

This module provides:
- DatabaseTask: Base task class with DB session management
- Recovery functions for interrupted tasks
"""

import logging
from typing import Optional

from celery import Task
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.celery_app.celery import celery_app
from app.core.config import settings

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """
    Base task class with database session management.

    Provides a database session that is automatically closed
    after the task completes.
    """

    _db_session: Optional[Session] = None

    @property
    def db(self) -> Session:
        """Get or create a database session."""
        if self._db_session is None:
            engine = create_engine(settings.DATABASE_URL)
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            self._db_session = SessionLocal()
        return self._db_session

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        """Clean up database session after task completion."""
        if self._db_session is not None:
            self._db_session.close()
            self._db_session = None


@celery_app.task(name="app.celery_app.tasks.base.recover_all_processing_tasks")
def recover_all_processing_tasks():
    """
    Recover all tasks that were interrupted (stuck in 'processing' status).

    This task is called when a worker starts up to handle tasks that
    were interrupted by a previous worker shutdown.
    """
    logger.info("Starting recovery of interrupted tasks...")

    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    total_recovered = 0

    try:
        # Recover each task type
        total_recovered += recover_transcription_tasks(db)
        total_recovered += recover_source_tasks(db)
        total_recovered += recover_minute_tasks(db)
        total_recovered += recover_document_check_tasks(db)
        total_recovered += recover_slide_project_tasks(db)
        total_recovered += recover_chat_message_tasks(db)

        logger.info(f"Recovery complete. Total recovered: {total_recovered} tasks.")

    except Exception as e:
        logger.error(f"Recovery failed: {e}", exc_info=True)
    finally:
        db.close()


def recover_transcription_tasks(db: Session) -> int:
    """
    Recover interrupted transcription tasks.

    Args:
        db: Database session

    Returns:
        Number of tasks recovered
    """
    from app.models.transcription import Transcription

    # Find tasks stuck in 'processing' status
    stuck_tasks = db.query(Transcription).filter(
        Transcription.processing_status == "processing"
    ).all()

    if not stuck_tasks:
        logger.info("No stuck transcription tasks found")
        return 0

    logger.info(f"Found {len(stuck_tasks)} stuck transcription tasks")

    recovered = 0
    for task in stuck_tasks:
        try:
            # Reset status to pending
            task.processing_status = "pending"
            task.processing_error = None
            db.commit()

            # Re-enqueue the task
            from app.celery_app.tasks.transcription import process_transcription_task
            process_transcription_task.delay(str(task.id))

            logger.info(f"Re-enqueued transcription task: {task.id}")
            recovered += 1

        except Exception as e:
            logger.error(f"Failed to recover task {task.id}: {e}")
            # Mark as failed instead
            task.processing_status = "failed"
            task.processing_error = f"Recovery failed: {str(e)}"
            db.commit()

    return recovered


def recover_source_tasks(db: Session) -> int:
    """
    Recover interrupted source processing tasks.

    Args:
        db: Database session

    Returns:
        Number of tasks recovered
    """
    from app.models.source import Source

    stuck_tasks = db.query(Source).filter(
        Source.processing_status == "processing"
    ).all()

    if not stuck_tasks:
        logger.info("No stuck source tasks found")
        return 0

    logger.info(f"Found {len(stuck_tasks)} stuck source tasks")

    recovered = 0
    for task in stuck_tasks:
        try:
            # For sources, we need raw_text to reprocess
            # If not available, mark as failed
            if not task.raw_text:
                task.processing_status = "failed"
                task.processing_error = "Recovery failed: raw_text not available"
                db.commit()
                continue

            task.processing_status = "pending"
            task.processing_error = None
            db.commit()

            from app.celery_app.tasks.content import process_source_task
            process_source_task.delay(str(task.id), task.raw_text)

            logger.info(f"Re-enqueued source task: {task.id}")
            recovered += 1

        except Exception as e:
            logger.error(f"Failed to recover source task {task.id}: {e}")
            task.processing_status = "failed"
            task.processing_error = f"Recovery failed: {str(e)}"
            db.commit()

    return recovered


def recover_minute_tasks(db: Session) -> int:
    """
    Recover interrupted minute processing tasks.

    Args:
        db: Database session

    Returns:
        Number of tasks recovered
    """
    from app.models.minute import Minute

    stuck_tasks = db.query(Minute).filter(
        Minute.processing_status == "processing"
    ).all()

    if not stuck_tasks:
        logger.info("No stuck minute tasks found")
        return 0

    logger.info(f"Found {len(stuck_tasks)} stuck minute tasks")

    recovered = 0
    for task in stuck_tasks:
        try:
            task.processing_status = "pending"
            task.processing_error = None
            db.commit()

            from app.celery_app.tasks.content import process_minute_task
            process_minute_task.delay(str(task.id))

            logger.info(f"Re-enqueued minute task: {task.id}")
            recovered += 1

        except Exception as e:
            logger.error(f"Failed to recover minute task {task.id}: {e}")
            task.processing_status = "failed"
            task.processing_error = f"Recovery failed: {str(e)}"
            db.commit()

    return recovered


def recover_document_check_tasks(db: Session) -> int:
    """
    Recover interrupted document check tasks.

    Args:
        db: Database session

    Returns:
        Number of tasks recovered
    """
    from app.models.document_check import DocumentCheck

    stuck_tasks = db.query(DocumentCheck).filter(
        DocumentCheck.status == "processing"
    ).all()

    if not stuck_tasks:
        logger.info("No stuck document check tasks found")
        return 0

    logger.info(f"Found {len(stuck_tasks)} stuck document check tasks")

    recovered = 0
    for task in stuck_tasks:
        try:
            task.status = "pending"
            task.error_message = None
            db.commit()

            from app.celery_app.tasks.document import process_document_check_task
            process_document_check_task.delay(str(task.id))

            logger.info(f"Re-enqueued document check task: {task.id}")
            recovered += 1

        except Exception as e:
            logger.error(f"Failed to recover document check task {task.id}: {e}")
            task.status = "failed"
            task.error_message = f"Recovery failed: {str(e)}"
            db.commit()

    return recovered


def recover_slide_project_tasks(db: Session) -> int:
    """
    Recover interrupted slide generation tasks.

    Args:
        db: Database session

    Returns:
        Number of tasks recovered
    """
    from app.models.slide_project import SlideProject

    stuck_tasks = db.query(SlideProject).filter(
        SlideProject.status == "generating"
    ).all()

    if not stuck_tasks:
        logger.info("No stuck slide project tasks found")
        return 0

    logger.info(f"Found {len(stuck_tasks)} stuck slide project tasks")

    recovered = 0
    for task in stuck_tasks:
        try:
            task.status = "pending"
            task.error_message = None
            db.commit()

            from app.celery_app.tasks.slide import process_slide_generation_task
            process_slide_generation_task.delay(str(task.id))

            logger.info(f"Re-enqueued slide project task: {task.id}")
            recovered += 1

        except Exception as e:
            logger.error(f"Failed to recover slide project task {task.id}: {e}")
            task.status = "failed"
            task.error_message = f"Recovery failed: {str(e)}"
            db.commit()

    return recovered


def recover_chat_message_tasks(db: Session) -> int:
    """
    Recover interrupted chat message tasks.

    Note: Chat messages are time-sensitive, so we mark them as failed
    rather than re-processing them after a worker restart.

    Args:
        db: Database session

    Returns:
        Number of tasks marked as failed
    """
    from app.models.chat import ChatMessage

    stuck_tasks = db.query(ChatMessage).filter(
        ChatMessage.status.in_(["pending", "generating"])
    ).all()

    if not stuck_tasks:
        logger.info("No stuck chat message tasks found")
        return 0

    logger.info(f"Found {len(stuck_tasks)} stuck chat message tasks")

    # For chat messages, we mark them as failed since they're time-sensitive
    # Users can re-ask their question
    for task in stuck_tasks:
        try:
            task.status = "failed"
            task.error_message = "サーバー再起動により処理が中断されました。再度質問してください。"
            db.commit()
            logger.info(f"Marked chat message as failed: {task.id}")

        except Exception as e:
            logger.error(f"Failed to update chat message {task.id}: {e}")

    return len(stuck_tasks)
