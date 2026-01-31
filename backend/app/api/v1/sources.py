import logging
import tempfile
import uuid
from pathlib import Path
from typing import List
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.celery_app.tasks.content import enqueue_source_processing
from app.core.config import settings
from app.core.deps import check_notebook_access, get_current_user, get_db
from app.core.exceptions import BadRequestError
from app.models.notebook import Notebook
from app.models.source import Source
from app.models.source_chunk import SourceChunk
from app.models.source_folder import SourceFolder
from app.models.user import User
from app.schemas.source import (
    SourceDetailOut,
    SourceListResponse,
    SourceOut,
    SourceSummaryUpdate,
    SourceUpdate,
    SourceUploadResponse,
)
from app.schemas.source_folder import SourceMoveRequest
from app.services.audit import AuditAction, TargetType, get_client_info, log_action
from app.services.embedding import embed_texts
from app.services.file_validator import FileValidationError, validate_uploaded_file
from app.services.text_chunker import chunk_pages_with_overlap
from app.services.storage import get_storage_service
from app.services.text_extractor import (
    extract_text_from_docx,
    extract_text_from_pdf,
    extract_text_from_txt,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sources", tags=["sources"])

# Allowed file extensions
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "md"}


@router.get("/notebook/{notebook_id}", response_model=SourceListResponse)
def list_sources(
    notebook_id: str,
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum items to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all sources in a notebook with pagination.
    """
    try:
        nb_uuid = UUID(notebook_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無効なNotebook IDです",
        )

    # Verify notebook access (owner or public)
    check_notebook_access(db, nb_uuid, current_user)

    # Get total count
    total = db.query(Source).filter(Source.notebook_id == nb_uuid).count()

    # Use LEFT JOIN to fetch sources with folder info in a single query (avoid N+1)
    sources_with_folders = (
        db.query(Source, SourceFolder)
        .outerjoin(SourceFolder, Source.folder_id == SourceFolder.id)
        .filter(Source.notebook_id == nb_uuid)
        .order_by(Source.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    # Build response with folder info included
    items = []
    for source, folder in sources_with_folders:
        source_out = SourceOut(
            id=source.id,
            notebook_id=source.notebook_id,
            title=source.title,
            file_type=source.file_type,
            folder_id=source.folder_id,
            folder_name=folder.name if folder else None,
            processing_status=source.processing_status,
            has_summary=source.summary is not None and len(source.summary) > 0,
            created_at=source.created_at,
        )
        items.append(source_out)

    return SourceListResponse(
        items=items,
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post(
    "/upload",
    response_model=SourceUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_source(
    request: Request,
    background_tasks: BackgroundTasks,
    notebook_id: str = Form(...),
    folder_id: str = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a source file (document) to a notebook.

    Supported file types: PDF, DOCX, TXT, MD
    All uploaded files are treated as documents.

    Security:
    - Validates file extension
    - Validates file content (magic bytes)
    - Checks for dangerous content in text files
    - Enforces file size limits
    """
    try:
        nb_uuid = UUID(notebook_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無効なNotebook IDです",
        )

    # Verify notebook access (owner or public)
    check_notebook_access(db, nb_uuid, current_user)

    # Read file content
    content = await file.read()

    # Comprehensive file validation (extension, magic bytes, size, content safety)
    try:
        file_type = validate_uploaded_file(
            filename=file.filename or "",
            content=content,
            allowed_extensions=ALLOWED_EXTENSIONS,
            max_size_mb=settings.MAX_UPLOAD_SIZE_MB,
        )
    except FileValidationError as e:
        logger.warning(
            f"File validation failed for user {current_user.id}: {e.message}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    # Get storage service
    storage = get_storage_service("uploads")

    # Generate unique file path
    src_id = uuid.uuid4()
    suffix = Path(file.filename or "").suffix.lower()
    storage_path = f"{src_id}{suffix}"

    # Write file to storage
    try:
        file_location = storage.upload(
            storage_path, content, file.content_type or "application/octet-stream"
        )
    except Exception as e:
        logger.error(f"Failed to write file to storage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ファイルの保存に失敗しました",
        )

    # Validate folder_id if provided
    folder_uuid = None
    if folder_id:
        try:
            folder_uuid = UUID(folder_id)
        except ValueError:
            try:
                storage.delete(storage_path)
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="無効なフォルダIDです",
            )
        folder = (
            db.query(SourceFolder)
            .filter(
                SourceFolder.id == folder_uuid,
                SourceFolder.notebook_id == nb_uuid,
            )
            .first()
        )
        if not folder:
            try:
                storage.delete(storage_path)
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="フォルダが見つからないか、このノートブックに属していません",
            )

    # Create source record
    source = Source(
        id=src_id,
        notebook_id=nb_uuid,
        folder_id=folder_uuid,
        title=file.filename,
        file_path=file_location,
        file_type=file_type,
        created_by=current_user.id,
    )

    try:
        db.add(source)
        db.commit()
        db.refresh(source)
    except Exception as e:
        # Rollback: delete the file if database insert fails
        logger.error(f"Database insert failed, rolling back file: {e}")
        try:
            storage.delete(storage_path)
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ソースの登録に失敗しました",
        )

    # Extract text based on file type
    # Use temporary file for text extraction (works with both local and cloud storage)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=suffix
        ) as temp_file:
            temp_file.write(content)
            temp_path = Path(temp_file.name)

        if file_type == "pdf":
            page_texts = extract_text_from_pdf(temp_path)
        elif file_type == "docx":
            page_texts = extract_text_from_docx(temp_path)
        else:
            page_texts = extract_text_from_txt(temp_path)

        # Clean up temp file
        if temp_path.exists():
            temp_path.unlink()
    except Exception as e:
        logger.error(f"Text extraction failed: {e}")
        # Clean up temp file
        if "temp_path" in locals() and temp_path.exists():
            temp_path.unlink()
        # Rollback: delete source and file
        db.delete(source)
        db.commit()
        try:
            storage.delete(storage_path)
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"テキスト抽出に失敗しました: {str(e)}",
        )

    # Combine all page texts into full_text for summary generation
    full_text = "\n\n".join([text for _, text in page_texts])

    # Split into chunks with semantic boundaries and overlap
    chunk_results = chunk_pages_with_overlap(
        page_texts=page_texts,
        chunk_size=2000,  # Smaller chunks for better retrieval precision
        overlap=200,  # 200 char overlap to maintain context across boundaries
    )

    chunks: List[SourceChunk] = []
    for chunk_result in chunk_results:
        chunks.append(
            SourceChunk(
                source_id=source.id,
                chunk_index=chunk_result.chunk_index,
                content=chunk_result.content,
                page_number=chunk_result.page_number,
            )
        )

    # Generate embeddings
    if chunks:
        try:
            contents = [c.content for c in chunks]
            embeddings = await embed_texts(contents)
            for c, emb in zip(chunks, embeddings):
                c.embedding = emb

            db.add_all(chunks)
            db.commit()
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            # Rollback: delete source and file
            db.delete(source)
            db.commit()
            try:
                storage.delete(storage_path)
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"埋め込み生成に失敗しました: {str(e)}",
            )

    # Trigger background processing for formatting and summary generation
    if full_text.strip():
        task_id = enqueue_source_processing(source.id, full_text)
        logger.info(
            f"Source processing enqueued: {source.id}, celery_task_id={task_id}"
        )

    # Log source upload
    ip_address, user_agent = get_client_info(request)
    log_action(
        db=db,
        action=AuditAction.UPLOAD_SOURCE,
        user_id=current_user.id,
        target_type=TargetType.SOURCE,
        target_id=str(source.id),
        details={
            "filename": file.filename,
            "file_type": file_type,
            "chunks_created": len(chunks),
            "notebook_id": notebook_id,
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )

    logger.info(
        f"Source uploaded: {file.filename} ({len(chunks)} chunks) "
        f"by user {current_user.id}"
    )

    # Get folder name if source is in a folder
    folder_name = None
    if source.folder_id:
        folder = (
            db.query(SourceFolder).filter(SourceFolder.id == source.folder_id).first()
        )
        if folder:
            folder_name = folder.name

    # Create response with has_summary field
    source_out = SourceOut(
        id=source.id,
        notebook_id=source.notebook_id,
        title=source.title,
        file_type=source.file_type,
        folder_id=source.folder_id,
        folder_name=folder_name,
        processing_status=source.processing_status,
        has_summary=False,  # Summary generation is async
        created_at=source.created_at,
    )

    return SourceUploadResponse(
        source=source_out,
        chunks_created=len(chunks),
    )


@router.patch("/{source_id}", response_model=SourceOut)
def update_source(
    source_id: str,
    data: SourceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a source's title.
    """
    try:
        src_uuid = UUID(source_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無効なソースIDです",
        )

    source = db.query(Source).filter(Source.id == src_uuid).first()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ソースが見つかりません",
        )

    # Verify notebook access (owner or public)
    check_notebook_access(db, source.notebook_id, current_user)

    if data.title is not None:
        source.title = data.title

    db.commit()
    db.refresh(source)

    # Get folder name if source is in a folder
    folder_name = None
    if source.folder_id:
        folder = (
            db.query(SourceFolder).filter(SourceFolder.id == source.folder_id).first()
        )
        if folder:
            folder_name = folder.name

    return SourceOut(
        id=source.id,
        notebook_id=source.notebook_id,
        title=source.title,
        file_type=source.file_type,
        folder_id=source.folder_id,
        folder_name=folder_name,
        processing_status=source.processing_status,
        has_summary=source.summary is not None and len(source.summary) > 0,
        created_at=source.created_at,
    )


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(
    source_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a source and its chunks.
    """
    ip_address, user_agent = get_client_info(request)

    try:
        src_uuid = UUID(source_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無効なソースIDです",
        )

    source = db.query(Source).filter(Source.id == src_uuid).first()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ソースが見つかりません",
        )

    # Verify notebook access (owner or public)
    check_notebook_access(db, source.notebook_id, current_user)

    source_title = source.title
    notebook_id = str(source.notebook_id)

    # Delete chunks first
    db.query(SourceChunk).filter(SourceChunk.source_id == src_uuid).delete()

    # Delete the source file from storage
    # Handle both old local paths and new storage paths for backward compatibility
    try:
        file_path_obj = Path(source.file_path)
        if file_path_obj.is_absolute() and file_path_obj.exists():
            # Legacy local file - delete directly
            file_path_obj.unlink()
        else:
            # New storage system - use storage service
            storage = get_storage_service("uploads")
            storage.delete(source.file_path)
    except Exception as e:
        logger.warning(f"Failed to delete source file from storage: {e}")

    # Delete the source record
    db.delete(source)
    db.commit()

    # Log source deletion
    log_action(
        db=db,
        action=AuditAction.DELETE_SOURCE,
        user_id=current_user.id,
        target_type=TargetType.SOURCE,
        target_id=source_id,
        details={"title": source_title, "notebook_id": notebook_id},
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return None


@router.get("/{source_id}/detail", response_model=SourceDetailOut)
def get_source_detail(
    source_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get source detail including summary information.
    """
    try:
        src_uuid = UUID(source_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無効なソースIDです",
        )

    source = db.query(Source).filter(Source.id == src_uuid).first()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ソースが見つかりません",
        )

    # Verify notebook access (owner or public)
    check_notebook_access(db, source.notebook_id, current_user)

    return SourceDetailOut(
        id=source.id,
        notebook_id=source.notebook_id,
        title=source.title,
        file_type=source.file_type,
        processing_status=source.processing_status,
        processing_error=source.processing_error,
        full_text=source.full_text,
        formatted_text=source.formatted_text,
        summary=source.summary,
        created_at=source.created_at,
    )


@router.patch("/{source_id}/summary", response_model=SourceDetailOut)
def update_source_summary(
    source_id: str,
    data: SourceSummaryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update source's formatted_text and/or summary.
    """
    try:
        src_uuid = UUID(source_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無効なソースIDです",
        )

    source = db.query(Source).filter(Source.id == src_uuid).first()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ソースが見つかりません",
        )

    # Verify notebook access (owner or public)
    check_notebook_access(db, source.notebook_id, current_user)

    if data.formatted_text is not None:
        source.formatted_text = data.formatted_text
    if data.summary is not None:
        source.summary = data.summary

    db.commit()
    db.refresh(source)

    logger.info(f"Source summary updated: {source_id} by user {current_user.id}")

    return SourceDetailOut(
        id=source.id,
        notebook_id=source.notebook_id,
        title=source.title,
        file_type=source.file_type,
        processing_status=source.processing_status,
        processing_error=source.processing_error,
        full_text=source.full_text,
        formatted_text=source.formatted_text,
        summary=source.summary,
        created_at=source.created_at,
    )


@router.patch("/{source_id}/move", response_model=SourceOut)
def move_source(
    source_id: str,
    data: SourceMoveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Move a source to a different folder or to root (no folder).

    Set folder_id to null to move to root.
    """
    try:
        src_uuid = UUID(source_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無効なソースIDです",
        )

    source = db.query(Source).filter(Source.id == src_uuid).first()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ソースが見つかりません",
        )

    # Verify notebook access (owner or public)
    check_notebook_access(db, source.notebook_id, current_user)

    # Validate folder_id if provided
    folder_name = None
    if data.folder_id:
        folder = (
            db.query(SourceFolder)
            .filter(
                SourceFolder.id == data.folder_id,
                SourceFolder.notebook_id == source.notebook_id,
            )
            .first()
        )
        if not folder:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="フォルダが見つからないか、このノートブックに属していません",
            )
        folder_name = folder.name

    # Update source folder
    source.folder_id = data.folder_id
    db.commit()
    db.refresh(source)

    logger.info(
        f"Source moved: {source_id} to folder {data.folder_id} by user {current_user.id}"
    )

    return SourceOut(
        id=source.id,
        notebook_id=source.notebook_id,
        title=source.title,
        file_type=source.file_type,
        folder_id=source.folder_id,
        folder_name=folder_name,
        processing_status=source.processing_status,
        has_summary=source.summary is not None and len(source.summary) > 0,
        created_at=source.created_at,
    )
