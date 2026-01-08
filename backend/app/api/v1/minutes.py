"""
Minutes API endpoints for managing meeting minutes.

Minutes are text-based records (not file uploads) that can be linked to documents.
"""
import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user, check_notebook_access, parse_uuid
from app.models.notebook import Notebook
from app.models.source import Source
from app.models.minute import Minute
from app.models.minute_document import MinuteDocument
from app.models.minute_chunk import MinuteChunk
from app.models.user import User
from app.schemas.minute import (
    MinuteCreate,
    MinuteUpdate,
    MinuteOut,
    MinuteListItem,
    MinuteDocumentsUpdate,
    MinuteDetailOut,
    MinuteSummaryUpdate,
)
from app.services.embedding import embed_texts
from app.services.audit import log_action, get_client_info, AuditAction, TargetType
from app.celery_app.tasks.content import enqueue_minute_processing

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/minutes", tags=["minutes"])

# Maximum characters per chunk for RAG
MAX_CHUNK_CHARS = 4000


def _verify_notebook_access(db: Session, notebook_id: UUID, user: User) -> Notebook:
    """Verify that the user can access the notebook (owner or public)."""
    return check_notebook_access(db, notebook_id, user)


def _get_minute_with_access_check(db: Session, minute_id: UUID, user: User) -> Minute:
    """Get a minute and verify the user can access the parent notebook."""
    minute = db.query(Minute).filter(Minute.id == minute_id).first()

    if not minute:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="議事録が見つかりません",
        )

    # Verify notebook access (owner or public)
    check_notebook_access(db, minute.notebook_id, user)

    return minute


def _get_document_ids(db: Session, minute_id: UUID) -> List[UUID]:
    """Get list of document IDs linked to a minute."""
    links = db.query(MinuteDocument.document_id).filter(
        MinuteDocument.minute_id == minute_id
    ).all()
    return [link[0] for link in links]


def _minute_to_out(minute: Minute, document_ids: List[UUID]) -> MinuteOut:
    """Convert a Minute model to MinuteOut schema."""
    return MinuteOut(
        id=minute.id,
        notebook_id=minute.notebook_id,
        title=minute.title,
        content=minute.content,
        document_ids=document_ids,
        processing_status=minute.processing_status,
        has_summary=minute.summary is not None and len(minute.summary) > 0,
        created_at=minute.created_at,
        updated_at=minute.updated_at,
    )


async def _create_chunks_with_embeddings(
    db: Session,
    minute_id: UUID,
    content: str,
) -> int:
    """
    Split content into chunks and create embeddings.
    Returns the number of chunks created.
    """
    # Split content into chunks
    chunks_data = []
    chunk_index = 0
    start = 0

    while start < len(content):
        chunk_text = content[start:start + MAX_CHUNK_CHARS]
        if chunk_text.strip():
            chunks_data.append({
                "minute_id": minute_id,
                "chunk_index": chunk_index,
                "content": chunk_text,
            })
            chunk_index += 1
        start += MAX_CHUNK_CHARS

    if not chunks_data:
        return 0

    # Generate embeddings
    contents = [c["content"] for c in chunks_data]
    embeddings = await embed_texts(contents)

    # Create chunk records
    for chunk_data, embedding in zip(chunks_data, embeddings):
        chunk = MinuteChunk(
            minute_id=chunk_data["minute_id"],
            chunk_index=chunk_data["chunk_index"],
            content=chunk_data["content"],
            embedding=embedding,
        )
        db.add(chunk)

    return len(chunks_data)


@router.get("/notebook/{notebook_id}", response_model=List[MinuteListItem])
def list_minutes(
    notebook_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all minutes in a notebook.
    """
    from sqlalchemy import func

    nb_uuid = parse_uuid(notebook_id, "Notebook ID")
    _verify_notebook_access(db, nb_uuid, current_user)

    minutes = db.query(Minute).filter(
        Minute.notebook_id == nb_uuid,
    ).order_by(Minute.created_at.desc()).all()

    if not minutes:
        return []

    # Batch fetch document counts to avoid N+1 queries
    minute_ids = [m.id for m in minutes]
    doc_counts = db.query(
        MinuteDocument.minute_id,
        func.count(MinuteDocument.document_id).label("count")
    ).filter(
        MinuteDocument.minute_id.in_(minute_ids)
    ).group_by(MinuteDocument.minute_id).all()

    doc_count_map = {row.minute_id: row.count for row in doc_counts}

    result = []
    for minute in minutes:
        result.append(MinuteListItem(
            id=minute.id,
            notebook_id=minute.notebook_id,
            title=minute.title,
            document_count=doc_count_map.get(minute.id, 0),
            processing_status=minute.processing_status,
            has_summary=minute.summary is not None and len(minute.summary) > 0,
            created_at=minute.created_at,
            updated_at=minute.updated_at,
        ))

    return result


@router.post("/notebook/{notebook_id}", response_model=MinuteOut, status_code=status.HTTP_201_CREATED)
async def create_minute(
    notebook_id: str,
    data: MinuteCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new minute with text content.

    The content will be chunked and embedded for RAG search.
    Optionally link to documents via document_ids.
    """
    ip_address, user_agent = get_client_info(request)
    nb_uuid = parse_uuid(notebook_id, "Notebook ID")
    _verify_notebook_access(db, nb_uuid, current_user)

    # Validate document_ids if provided
    if data.document_ids:
        # Check that all documents exist and belong to the same notebook
        for doc_id in data.document_ids:
            source = db.query(Source).filter(
                Source.id == doc_id,
                Source.notebook_id == nb_uuid,
            ).first()
            if not source:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"資料 {doc_id} が見つからないか、このノートブックに属していません",
                )

    # Create minute record
    minute = Minute(
        notebook_id=nb_uuid,
        created_by=current_user.id,
        title=data.title,
        content=data.content,
    )
    db.add(minute)
    db.flush()  # Get the ID

    # Create document links
    for doc_id in data.document_ids:
        link = MinuteDocument(
            minute_id=minute.id,
            document_id=doc_id,
        )
        db.add(link)

    # Create chunks with embeddings
    try:
        chunks_count = await _create_chunks_with_embeddings(db, minute.id, data.content)
    except Exception as e:
        logger.error(f"Failed to create embeddings for minute: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"埋め込み生成に失敗しました: {str(e)}",
        )

    db.commit()
    db.refresh(minute)

    # Log action
    log_action(
        db=db,
        action=AuditAction.CREATE_MINUTE,
        user_id=current_user.id,
        target_type=TargetType.MINUTE,
        target_id=str(minute.id),
        details={
            "title": minute.title,
            "content_length": len(data.content),
            "chunks_created": chunks_count,
            "documents_linked": len(data.document_ids),
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )

    logger.info(
        f"Minute created: {minute.title} ({chunks_count} chunks) "
        f"by user {current_user.id}"
    )

    # Trigger background processing for formatting and summary generation
    if data.content.strip():
        task_id = enqueue_minute_processing(minute.id)
        logger.info(f"Minute processing enqueued: {minute.id}, celery_task_id={task_id}")

    return _minute_to_out(minute, data.document_ids)


@router.get("/{minute_id}", response_model=MinuteOut)
def get_minute(
    minute_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific minute by ID.
    """
    m_uuid = parse_uuid(minute_id, "Minute ID")
    minute = _get_minute_with_access_check(db, m_uuid, current_user)
    document_ids = _get_document_ids(db, minute.id)

    return _minute_to_out(minute, document_ids)


@router.patch("/{minute_id}", response_model=MinuteOut)
async def update_minute(
    minute_id: str,
    data: MinuteUpdate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a minute's title and/or content.

    If content is updated, chunks will be regenerated.
    """
    ip_address, user_agent = get_client_info(request)
    m_uuid = parse_uuid(minute_id, "Minute ID")
    minute = _get_minute_with_access_check(db, m_uuid, current_user)

    content_updated = False

    if data.title is not None:
        minute.title = data.title

    if data.content is not None and data.content != minute.content:
        minute.content = data.content
        content_updated = True

        # Delete old chunks
        db.query(MinuteChunk).filter(MinuteChunk.minute_id == minute.id).delete()

        # Create new chunks with embeddings
        try:
            chunks_count = await _create_chunks_with_embeddings(db, minute.id, data.content)
        except Exception as e:
            logger.error(f"Failed to regenerate embeddings for minute: {e}")
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"埋め込み生成に失敗しました: {str(e)}",
            )

    db.commit()
    db.refresh(minute)

    # Log action
    log_action(
        db=db,
        action=AuditAction.UPDATE_MINUTE,
        user_id=current_user.id,
        target_type=TargetType.MINUTE,
        target_id=str(minute.id),
        details={
            "title": minute.title,
            "content_updated": content_updated,
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )

    # Trigger background processing when content is updated
    if content_updated and minute.content.strip():
        # Reset summary fields since content changed
        minute.formatted_content = None
        minute.summary = None
        minute.processing_status = "pending"
        minute.processing_error = None
        db.commit()

        task_id = enqueue_minute_processing(minute.id)
        logger.info(f"Minute processing enqueued for updated minute: {minute.id}, celery_task_id={task_id}")

    document_ids = _get_document_ids(db, minute.id)
    return _minute_to_out(minute, document_ids)


@router.put("/{minute_id}/documents", response_model=MinuteOut)
def update_minute_documents(
    minute_id: str,
    data: MinuteDocumentsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update the documents linked to a minute.

    Replaces all existing links with the provided document_ids.
    """
    m_uuid = parse_uuid(minute_id, "Minute ID")
    minute = _get_minute_with_access_check(db, m_uuid, current_user)

    # Validate document_ids
    for doc_id in data.document_ids:
        source = db.query(Source).filter(
            Source.id == doc_id,
            Source.notebook_id == minute.notebook_id,
        ).first()
        if not source:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"資料 {doc_id} が見つからないか、このノートブックに属していません",
            )

    # Delete existing links
    db.query(MinuteDocument).filter(MinuteDocument.minute_id == minute.id).delete()

    # Create new links
    for doc_id in data.document_ids:
        link = MinuteDocument(
            minute_id=minute.id,
            document_id=doc_id,
        )
        db.add(link)

    db.commit()
    db.refresh(minute)

    return _minute_to_out(minute, data.document_ids)


@router.delete("/{minute_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_minute(
    minute_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a minute and all its chunks and document links.
    """
    ip_address, user_agent = get_client_info(request)
    m_uuid = parse_uuid(minute_id, "Minute ID")
    minute = _get_minute_with_access_check(db, m_uuid, current_user)

    title = minute.title

    # Delete chunks (cascade should handle this, but be explicit)
    db.query(MinuteChunk).filter(MinuteChunk.minute_id == minute.id).delete()

    # Delete document links
    db.query(MinuteDocument).filter(MinuteDocument.minute_id == minute.id).delete()

    # Delete minute
    db.delete(minute)
    db.commit()

    # Log action
    log_action(
        db=db,
        action=AuditAction.DELETE_MINUTE,
        user_id=current_user.id,
        target_type=TargetType.MINUTE,
        target_id=minute_id,
        details={"title": title},
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return None


@router.get("/{minute_id}/detail", response_model=MinuteDetailOut)
def get_minute_detail(
    minute_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get minute detail including summary information.
    """
    m_uuid = parse_uuid(minute_id, "Minute ID")
    minute = _get_minute_with_access_check(db, m_uuid, current_user)
    document_ids = _get_document_ids(db, minute.id)

    return MinuteDetailOut(
        id=minute.id,
        notebook_id=minute.notebook_id,
        title=minute.title,
        content=minute.content,
        document_ids=document_ids,
        processing_status=minute.processing_status,
        processing_error=minute.processing_error,
        formatted_content=minute.formatted_content,
        summary=minute.summary,
        created_at=minute.created_at,
        updated_at=minute.updated_at,
    )


@router.patch("/{minute_id}/summary", response_model=MinuteDetailOut)
def update_minute_summary(
    minute_id: str,
    data: MinuteSummaryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update minute's formatted_content and/or summary.
    """
    m_uuid = parse_uuid(minute_id, "Minute ID")
    minute = _get_minute_with_access_check(db, m_uuid, current_user)

    if data.formatted_content is not None:
        minute.formatted_content = data.formatted_content
    if data.summary is not None:
        minute.summary = data.summary

    db.commit()
    db.refresh(minute)

    logger.info(f"Minute summary updated: {minute_id} by user {current_user.id}")

    document_ids = _get_document_ids(db, minute.id)
    return MinuteDetailOut(
        id=minute.id,
        notebook_id=minute.notebook_id,
        title=minute.title,
        content=minute.content,
        document_ids=document_ids,
        processing_status=minute.processing_status,
        processing_error=minute.processing_error,
        formatted_content=minute.formatted_content,
        summary=minute.summary,
        created_at=minute.created_at,
        updated_at=minute.updated_at,
    )
