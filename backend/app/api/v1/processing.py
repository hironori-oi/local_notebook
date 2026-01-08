"""
Processing Status API - Monitor background processing of sources and minutes
"""

from datetime import datetime, timedelta
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.celery_app.tasks.content import (
    enqueue_minute_processing,
    enqueue_source_processing,
)
from app.core.deps import get_current_user, get_db
from app.models.minute import Minute
from app.models.notebook import Notebook
from app.models.source import Source
from app.models.user import User

router = APIRouter(prefix="/processing", tags=["processing"])


class ProcessingItem(BaseModel):
    id: str
    type: Literal["source", "minute"]
    title: str
    notebook_id: str
    notebook_title: str
    status: str
    error: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ProcessingStats(BaseModel):
    pending: int
    processing: int
    completed_today: int
    failed_today: int


class ProcessingDashboard(BaseModel):
    stats: ProcessingStats
    items: list[ProcessingItem]


@router.get("/stats", response_model=ProcessingStats)
async def get_processing_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProcessingStats:
    """Get processing statistics (lightweight endpoint for badge)"""
    user_id = current_user.id

    # Get user's notebooks as proper select statement
    user_notebooks_select = select(Notebook.id).where(Notebook.owner_id == user_id)

    # Today's date range
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Source stats
    source_pending = (
        db.query(func.count(Source.id))
        .filter(
            Source.notebook_id.in_(user_notebooks_select),
            Source.processing_status == "pending",
        )
        .scalar()
        or 0
    )

    source_processing = (
        db.query(func.count(Source.id))
        .filter(
            Source.notebook_id.in_(user_notebooks_select),
            Source.processing_status == "processing",
        )
        .scalar()
        or 0
    )

    # Source model doesn't have updated_at, use created_at instead
    source_completed_today = (
        db.query(func.count(Source.id))
        .filter(
            Source.notebook_id.in_(user_notebooks_select),
            Source.processing_status == "completed",
            Source.created_at >= today_start,
        )
        .scalar()
        or 0
    )

    source_failed_today = (
        db.query(func.count(Source.id))
        .filter(
            Source.notebook_id.in_(user_notebooks_select),
            Source.processing_status == "failed",
            Source.created_at >= today_start,
        )
        .scalar()
        or 0
    )

    # Minute stats
    minute_pending = (
        db.query(func.count(Minute.id))
        .filter(
            Minute.notebook_id.in_(user_notebooks_select),
            Minute.processing_status == "pending",
        )
        .scalar()
        or 0
    )

    minute_processing = (
        db.query(func.count(Minute.id))
        .filter(
            Minute.notebook_id.in_(user_notebooks_select),
            Minute.processing_status == "processing",
        )
        .scalar()
        or 0
    )

    minute_completed_today = (
        db.query(func.count(Minute.id))
        .filter(
            Minute.notebook_id.in_(user_notebooks_select),
            Minute.processing_status == "completed",
            Minute.updated_at >= today_start,
        )
        .scalar()
        or 0
    )

    minute_failed_today = (
        db.query(func.count(Minute.id))
        .filter(
            Minute.notebook_id.in_(user_notebooks_select),
            Minute.processing_status == "failed",
            Minute.updated_at >= today_start,
        )
        .scalar()
        or 0
    )

    return ProcessingStats(
        pending=source_pending + minute_pending,
        processing=source_processing + minute_processing,
        completed_today=source_completed_today + minute_completed_today,
        failed_today=source_failed_today + minute_failed_today,
    )


@router.get("/dashboard", response_model=ProcessingDashboard)
async def get_processing_dashboard(
    status: str = Query("all", pattern="^(all|pending|processing|completed|failed)$"),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProcessingDashboard:
    """Get processing dashboard with items and stats"""
    user_id = current_user.id

    # Get stats first
    stats = await get_processing_stats(current_user, db)

    # Build items list
    items: list[ProcessingItem] = []

    # Get user's notebooks with titles
    user_notebooks = db.query(Notebook).filter(Notebook.owner_id == user_id).all()
    notebook_map = {str(nb.id): nb.title for nb in user_notebooks}
    notebook_ids = list(notebook_map.keys())

    if not notebook_ids:
        return ProcessingDashboard(stats=stats, items=[])

    # Status filter
    status_filter = None
    if status != "all":
        status_filter = status

    # Get sources
    source_query = db.query(Source).filter(
        Source.notebook_id.in_([UUID(nid) for nid in notebook_ids])
    )
    if status_filter:
        source_query = source_query.filter(Source.processing_status == status_filter)

    sources = source_query.order_by(Source.created_at.desc()).limit(limit).all()

    for source in sources:
        items.append(
            ProcessingItem(
                id=str(source.id),
                type="source",
                title=source.title,
                notebook_id=str(source.notebook_id),
                notebook_title=notebook_map.get(str(source.notebook_id), "Unknown"),
                status=source.processing_status or "pending",
                error=source.processing_error,
                created_at=source.created_at,
            )
        )

    # Get minutes
    minute_query = db.query(Minute).filter(
        Minute.notebook_id.in_([UUID(nid) for nid in notebook_ids])
    )
    if status_filter:
        minute_query = minute_query.filter(Minute.processing_status == status_filter)

    minutes = minute_query.order_by(Minute.created_at.desc()).limit(limit).all()

    for minute in minutes:
        items.append(
            ProcessingItem(
                id=str(minute.id),
                type="minute",
                title=minute.title,
                notebook_id=str(minute.notebook_id),
                notebook_title=notebook_map.get(str(minute.notebook_id), "Unknown"),
                status=minute.processing_status or "pending",
                error=minute.processing_error,
                created_at=minute.created_at,
            )
        )

    # Sort by created_at descending and limit
    items.sort(key=lambda x: x.created_at, reverse=True)
    items = items[:limit]

    return ProcessingDashboard(stats=stats, items=items)


@router.post("/retry/{item_type}/{item_id}")
async def retry_processing(
    item_type: Literal["source", "minute"],
    item_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retry failed processing for a source or minute"""
    user_id = current_user.id
    item_uuid = UUID(item_id)

    if item_type == "source":
        source = db.query(Source).filter(Source.id == item_uuid).first()
        if not source:
            raise HTTPException(status_code=404, detail="ソースが見つかりません")

        # Check ownership
        notebook = db.query(Notebook).filter(Notebook.id == source.notebook_id).first()
        if not notebook or notebook.owner_id != user_id:
            raise HTTPException(status_code=403, detail="アクセス権限がありません")

        if source.processing_status not in ["failed", "pending"]:
            raise HTTPException(
                status_code=400,
                detail="失敗またはペンディング状態の項目のみリトライできます",
            )

        # Reset status and schedule reprocessing
        source.processing_status = "pending"
        source.processing_error = None
        db.commit()

        # Schedule Celery task
        if source.full_text:
            enqueue_source_processing(source.id, source.full_text)

        return {"message": "Retry scheduled", "id": item_id, "type": "source"}

    else:  # minute
        minute = db.query(Minute).filter(Minute.id == item_uuid).first()
        if not minute:
            raise HTTPException(status_code=404, detail="議事録が見つかりません")

        # Check ownership
        notebook = db.query(Notebook).filter(Notebook.id == minute.notebook_id).first()
        if not notebook or notebook.owner_id != user_id:
            raise HTTPException(status_code=403, detail="アクセス権限がありません")

        if minute.processing_status not in ["failed", "pending"]:
            raise HTTPException(
                status_code=400,
                detail="失敗またはペンディング状態の項目のみリトライできます",
            )

        # Reset status and schedule reprocessing
        minute.processing_status = "pending"
        minute.processing_error = None
        db.commit()

        # Schedule Celery task
        enqueue_minute_processing(minute.id)

        return {"message": "Retry scheduled", "id": item_id, "type": "minute"}
