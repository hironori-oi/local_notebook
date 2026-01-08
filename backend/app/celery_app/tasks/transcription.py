"""
Celery tasks for YouTube video transcription.

This module provides tasks for:
- Processing transcription requests
- Downloading audio from YouTube
- Transcribing audio via Whisper server
- Formatting text with LLM
"""

import logging
import asyncio
from uuid import UUID

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError

from app.celery_app.tasks.base import DatabaseTask
from app.celery_app.config import RETRY_CONFIG, RETRYABLE_EXCEPTIONS

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    base=DatabaseTask,
    name="app.celery_app.tasks.transcription.process_transcription",
    queue="transcription",
    autoretry_for=RETRYABLE_EXCEPTIONS,
    **RETRY_CONFIG,
)
def process_transcription_task(self, transcription_id: str):
    """
    Process a transcription request.

    This task:
    1. Downloads audio from YouTube
    2. Transcribes audio using Whisper server
    3. Formats text using LLM
    4. Updates database with results

    Args:
        transcription_id: UUID string of the transcription record
    """
    from app.models.transcription import Transcription
    from app.services.youtube_transcriber import (
        download_youtube_audio,
        transcribe_audio,
        format_transcript_with_llm,
    )

    logger.info(f"Processing transcription task: {transcription_id}")

    # Get database session from base class
    db = self.db
    audio_path = None

    try:
        # Get transcription record
        transcription = db.query(Transcription).filter(
            Transcription.id == UUID(transcription_id)
        ).first()

        if not transcription:
            logger.error(f"Transcription not found: {transcription_id}")
            return {"status": "error", "message": "Transcription not found"}

        # Update status to processing
        transcription.processing_status = "processing"
        db.commit()

        # Run async operations in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Step 1: Download audio
            logger.info(f"Downloading audio for {transcription_id}")
            audio_path, video_info = loop.run_until_complete(
                download_youtube_audio(
                    transcription.youtube_url,
                    transcription.video_id,
                )
            )

            # Update video title
            transcription.video_title = video_info.get("title")
            db.commit()

            # Step 2: Transcribe audio
            logger.info(f"Transcribing audio for {transcription_id}")
            raw_text = loop.run_until_complete(transcribe_audio(audio_path))
            transcription.raw_transcript = raw_text
            db.commit()

            # Step 3: Format with LLM
            logger.info(f"Formatting transcript for {transcription_id}")
            formatted_text = loop.run_until_complete(
                format_transcript_with_llm(raw_text)
            )
            transcription.formatted_transcript = formatted_text

            # Mark as completed
            transcription.processing_status = "completed"
            transcription.processing_error = None
            db.commit()

            logger.info(f"Transcription completed: {transcription_id}")
            return {"status": "completed", "transcription_id": transcription_id}

        finally:
            loop.close()

    except RETRYABLE_EXCEPTIONS as e:
        logger.warning(
            f"Retryable error for {transcription_id}: {e}, "
            f"attempt {self.request.retries + 1}/{RETRY_CONFIG['max_retries'] + 1}"
        )
        # Let Celery handle the retry
        raise

    except MaxRetriesExceededError:
        logger.error(f"Max retries exceeded for {transcription_id}")
        _mark_transcription_failed(
            db, transcription_id,
            "処理の最大再試行回数を超えました。しばらく経ってから再試行してください。"
        )
        return {"status": "failed", "message": "Max retries exceeded"}

    except ValueError as e:
        # Non-retryable validation errors
        logger.error(f"Validation error for {transcription_id}: {e}")
        _mark_transcription_failed(db, transcription_id, str(e))
        return {"status": "failed", "message": str(e)}

    except Exception as e:
        logger.error(f"Transcription failed for {transcription_id}: {e}", exc_info=True)
        _mark_transcription_failed(db, transcription_id, str(e))
        return {"status": "failed", "message": str(e)}

    finally:
        # Clean up audio file
        if audio_path:
            import os
            if os.path.exists(audio_path):
                try:
                    os.unlink(audio_path)
                    logger.debug(f"Cleaned up audio file: {audio_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up audio file: {e}")


def _mark_transcription_failed(db, transcription_id: str, error_message: str):
    """Mark a transcription as failed in the database."""
    from app.models.transcription import Transcription

    try:
        transcription = db.query(Transcription).filter(
            Transcription.id == UUID(transcription_id)
        ).first()

        if transcription:
            transcription.processing_status = "failed"
            transcription.processing_error = error_message
            db.commit()
    except Exception as e:
        logger.error(f"Failed to update error status: {e}")


def enqueue_transcription(transcription_id: UUID) -> str:
    """
    Enqueue a transcription task for processing.

    This is the main entry point for API endpoints to
    start transcription processing.

    Args:
        transcription_id: UUID of the transcription record

    Returns:
        Celery task ID
    """
    result = process_transcription_task.delay(str(transcription_id))
    logger.info(f"Enqueued transcription task: {transcription_id}, celery_task_id: {result.id}")
    return result.id
