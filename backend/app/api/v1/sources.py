import logging
from pathlib import Path
from typing import List
from uuid import UUID
import uuid

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.core.config import settings
from app.core.exceptions import BadRequestError
from app.models.source import Source
from app.models.source_chunk import SourceChunk
from app.models.notebook import Notebook
from app.models.user import User
from app.schemas.source import SourceUploadResponse, SourceOut, SourceUpdate
from app.services.text_extractor import (
    extract_text_from_pdf,
    extract_text_from_docx,
    extract_text_from_txt,
)
from app.services.embedding import embed_texts
from app.services.file_validator import (
    validate_uploaded_file,
    FileValidationError,
)
from app.services.audit import log_action, get_client_info, AuditAction, TargetType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sources", tags=["sources"])

# Allowed file extensions
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "md"}


@router.get("/notebook/{notebook_id}", response_model=List[SourceOut])
def list_sources(
    notebook_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all sources in a notebook.
    """
    try:
        nb_uuid = UUID(notebook_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無効なNotebook IDです",
        )

    # Verify notebook ownership
    notebook = db.query(Notebook).filter(
        Notebook.id == nb_uuid,
        Notebook.owner_id == current_user.id,
    ).first()

    if not notebook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notebookが見つかりません",
        )

    sources = db.query(Source).filter(Source.notebook_id == nb_uuid).all()
    return sources


@router.post(
    "/upload",
    response_model=SourceUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_source(
    request: Request,
    notebook_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a source file to a notebook.

    Supported file types: PDF, DOCX, TXT, MD

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

    # Verify notebook ownership
    notebook = db.query(Notebook).filter(
        Notebook.id == nb_uuid,
        Notebook.owner_id == current_user.id,
    ).first()

    if not notebook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notebookが見つかりません",
        )

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

    # Create upload directory if it doesn't exist
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique file path
    src_id = uuid.uuid4()
    suffix = Path(file.filename or "").suffix.lower()
    dest_path = upload_dir / f"{src_id}{suffix}"

    # Write file to disk
    try:
        with dest_path.open("wb") as f:
            f.write(content)
    except IOError as e:
        logger.error(f"Failed to write file to disk: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ファイルの保存に失敗しました",
        )

    # Create source record
    source = Source(
        id=src_id,
        notebook_id=nb_uuid,
        title=file.filename,
        file_path=str(dest_path),
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
        if dest_path.exists():
            dest_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ソースの登録に失敗しました",
        )

    # Extract text based on file type
    try:
        if file_type == "pdf":
            page_texts = extract_text_from_pdf(dest_path)
        elif file_type == "docx":
            page_texts = extract_text_from_docx(dest_path)
        else:
            page_texts = extract_text_from_txt(dest_path)
    except Exception as e:
        logger.error(f"Text extraction failed: {e}")
        # Rollback: delete source and file
        db.delete(source)
        db.commit()
        if dest_path.exists():
            dest_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"テキスト抽出に失敗しました: {str(e)}",
        )

    # Split into chunks
    chunks: List[SourceChunk] = []
    max_chars = 4000
    chunk_index = 0
    for page_number, text in page_texts:
        start = 0
        while start < len(text):
            part = text[start : start + max_chars]
            if part.strip():
                chunks.append(
                    SourceChunk(
                        source_id=source.id,
                        chunk_index=chunk_index,
                        content=part,
                        page_number=page_number,
                    )
                )
                chunk_index += 1
            start += max_chars

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
            if dest_path.exists():
                dest_path.unlink()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"埋め込み生成に失敗しました: {str(e)}",
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

    return SourceUploadResponse(
        source=SourceOut.model_validate(source),
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

    # Verify notebook ownership
    notebook = db.query(Notebook).filter(
        Notebook.id == source.notebook_id,
        Notebook.owner_id == current_user.id,
    ).first()

    if not notebook:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="このソースを更新する権限がありません",
        )

    source.title = data.title
    db.commit()
    db.refresh(source)

    return source


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

    # Verify notebook ownership
    notebook = db.query(Notebook).filter(
        Notebook.id == source.notebook_id,
        Notebook.owner_id == current_user.id,
    ).first()

    if not notebook:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="このソースを削除する権限がありません",
        )

    source_title = source.title
    notebook_id = str(source.notebook_id)

    # Delete chunks first
    db.query(SourceChunk).filter(SourceChunk.source_id == src_uuid).delete()

    # Delete the source file if it exists
    file_path = Path(source.file_path)
    if file_path.exists():
        file_path.unlink()

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
