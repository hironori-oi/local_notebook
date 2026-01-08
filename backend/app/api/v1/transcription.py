"""
API endpoints for YouTube video transcription.
"""

import logging
import math
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.celery_app.tasks.transcription import enqueue_transcription
from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.models.transcription import Transcription
from app.models.user import User
from app.schemas.transcription import (TranscriptionCreate,
                                       TranscriptionListItem,
                                       TranscriptionListResponse,
                                       TranscriptionResponse)
from app.services.youtube_transcriber import (extract_video_id,
                                              is_whisper_configured)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transcriptions", tags=["transcriptions"])


@router.get("/status/config")
async def get_transcription_config_status():
    """
    Check if the transcription service is configured and available.
    """
    return {
        "configured": is_whisper_configured(),
        "whisper_server_url": (
            settings.WHISPER_SERVER_URL if is_whisper_configured() else None
        ),
    }


@router.post(
    "/", response_model=TranscriptionResponse, status_code=status.HTTP_201_CREATED
)
async def create_transcription(
    req: TranscriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new transcription request.

    The transcription will be processed in the background:
    1. Download audio from YouTube
    2. Transcribe using Whisper
    3. Format text using LLM

    Check the status using GET /transcriptions/{id}
    """
    # Check if Whisper server is configured
    if not is_whisper_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="文字起こしサーバーが設定されていません。管理者に連絡してください。",
        )

    # Extract video ID
    video_id = extract_video_id(req.youtube_url)
    if not video_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="有効なYouTube URLを入力してください",
        )

    # Check for duplicate (same video_id for same user in pending/processing state)
    existing = (
        db.query(Transcription)
        .filter(
            Transcription.user_id == current_user.id,
            Transcription.video_id == video_id,
            Transcription.processing_status.in_(["pending", "processing"]),
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="この動画は既に処理中です",
        )

    # Create transcription record
    transcription = Transcription(
        user_id=current_user.id,
        youtube_url=req.youtube_url,
        video_id=video_id,
        processing_status="pending",
    )
    db.add(transcription)
    db.commit()
    db.refresh(transcription)

    # Enqueue transcription task via Celery
    task_id = enqueue_transcription(transcription.id)

    logger.info(
        f"Created transcription {transcription.id} for user {current_user.id}, "
        f"celery_task_id={task_id}"
    )

    return transcription


@router.get("/", response_model=TranscriptionListResponse)
async def list_transcriptions(
    page: int = 1,
    per_page: int = 20,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List transcriptions for the current user.

    Supports pagination and optional status filtering.
    """
    if page < 1:
        page = 1
    if per_page < 1 or per_page > 100:
        per_page = 20

    # Base query
    query = db.query(Transcription).filter(Transcription.user_id == current_user.id)

    # Apply status filter
    if status_filter and status_filter in [
        "pending",
        "processing",
        "completed",
        "failed",
    ]:
        query = query.filter(Transcription.processing_status == status_filter)

    # Get total count
    total = query.count()

    # Get paginated results
    items = (
        query.order_by(Transcription.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return TranscriptionListResponse(
        items=[TranscriptionListItem.model_validate(item) for item in items],
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total > 0 else 0,
    )


@router.get("/{transcription_id}", response_model=TranscriptionResponse)
async def get_transcription(
    transcription_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific transcription by ID.
    """
    transcription = (
        db.query(Transcription)
        .filter(
            Transcription.id == transcription_id,
            Transcription.user_id == current_user.id,
        )
        .first()
    )

    if not transcription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文字起こしが見つかりません",
        )

    return transcription


@router.delete("/{transcription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transcription(
    transcription_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a transcription.

    Note: If the transcription is currently processing, the background
    task will continue but the result will not be saved.
    """
    transcription = (
        db.query(Transcription)
        .filter(
            Transcription.id == transcription_id,
            Transcription.user_id == current_user.id,
        )
        .first()
    )

    if not transcription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文字起こしが見つかりません",
        )

    db.delete(transcription)
    db.commit()

    logger.info(f"Deleted transcription {transcription_id}")


@router.post("/{transcription_id}/retry", response_model=TranscriptionResponse)
async def retry_transcription(
    transcription_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retry a failed transcription.

    Only works for transcriptions with 'failed' status.
    """
    # Check if Whisper server is configured
    if not is_whisper_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="文字起こしサーバーが設定されていません。管理者に連絡してください。",
        )

    transcription = (
        db.query(Transcription)
        .filter(
            Transcription.id == transcription_id,
            Transcription.user_id == current_user.id,
        )
        .first()
    )

    if not transcription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文字起こしが見つかりません",
        )

    if transcription.processing_status != "failed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="失敗した文字起こしのみリトライできます",
        )

    # Reset status
    transcription.processing_status = "pending"
    transcription.processing_error = None
    db.commit()

    # Enqueue transcription task via Celery
    task_id = enqueue_transcription(transcription.id)

    logger.info(f"Retrying transcription {transcription_id}, celery_task_id={task_id}")

    db.refresh(transcription)
    return transcription
