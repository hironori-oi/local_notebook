"""
Document Checker API - Upload and check documents for issues.

Supports PDF and PowerPoint files.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import (APIRouter, BackgroundTasks, Depends, File, Form,
                     HTTPException, Query, UploadFile, status)
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.celery_app.tasks.document import enqueue_document_check
from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.models.document_check import (DocumentCheck, DocumentCheckIssue,
                                       UserCheckPreference)
from app.models.user import User
from app.schemas.document_check import (CheckTypeInfo, CheckTypesResponse,
                                        DocumentCheckDetail,
                                        DocumentCheckIssueOut,
                                        DocumentCheckListResponse,
                                        DocumentCheckSummary,
                                        DocumentCheckUploadResponse,
                                        IssueUpdateRequest,
                                        IssueUpdateResponse,
                                        UserCheckPreferenceOut,
                                        UserCheckPreferenceUpdate)
from app.services.document_checker import (CHECK_TYPES, get_check_types_info,
                                           get_default_check_types)
from app.services.file_validator import (FileValidationError,
                                         validate_file_extension,
                                         validate_file_size,
                                         validate_magic_bytes)
from app.services.pptx_extractor import extract_text_from_pptx
from app.services.text_extractor import extract_text_from_pdf_bytes

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/document-checker", tags=["document-checker"])

# Allowed file extensions for document checker
ALLOWED_EXTENSIONS = {"pdf", "pptx"}

# Magic bytes for PPTX (ZIP format)
PPTX_MAGIC_BYTES = [
    (b"PK\x03\x04", 0, "PPTX/Office Open XML"),
    (b"PK\x05\x06", 0, "PPTX/Office Open XML (empty)"),
    (b"PK\x07\x08", 0, "PPTX/Office Open XML (spanned)"),
]


def _validate_pptx_magic_bytes(content: bytes) -> bool:
    """Validate PPTX file magic bytes."""
    for magic_bytes, offset, _ in PPTX_MAGIC_BYTES:
        if len(content) >= offset + len(magic_bytes):
            if content[offset : offset + len(magic_bytes)] == magic_bytes:
                return True
    return False


@router.get("/check-types", response_model=CheckTypesResponse)
async def get_check_types():
    """Get available check types."""
    check_types = get_check_types_info()
    return CheckTypesResponse(check_types=check_types)


@router.post(
    "/upload",
    response_model=DocumentCheckUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    check_types: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a document for checking.

    Supported file types: PDF, PPTX
    """
    # Read file content
    content = await file.read()

    # Validate file extension
    try:
        file_type = validate_file_extension(
            filename=file.filename or "",
            allowed_extensions=ALLOWED_EXTENSIONS,
        )
    except FileValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    # Validate file size
    try:
        validate_file_size(content, settings.MAX_UPLOAD_SIZE_MB)
    except FileValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    # Validate magic bytes
    if file_type == "pdf":
        if not validate_magic_bytes(content, "pdf"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ファイルの内容がPDFではありません",
            )
    elif file_type == "pptx":
        if not _validate_pptx_magic_bytes(content):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ファイルの内容がPowerPointではありません",
            )

    # Extract text from document
    try:
        if file_type == "pdf":
            extracted_text, page_count = extract_text_from_pdf_bytes(content)
        elif file_type == "pptx":
            extracted_text, slides_data = extract_text_from_pptx(content)
            page_count = len(slides_data)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"サポートされていないファイル形式です: {file_type}",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Text extraction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"テキスト抽出に失敗しました: {str(e)}",
        )

    if not extracted_text or not extracted_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ドキュメントからテキストを抽出できませんでした",
        )

    # Parse check types
    enabled_check_types = []
    if check_types:
        enabled_check_types = [
            ct.strip() for ct in check_types.split(",") if ct.strip() in CHECK_TYPES
        ]
    if not enabled_check_types:
        enabled_check_types = get_default_check_types()

    # Create document check record
    document = DocumentCheck(
        user_id=current_user.id,
        filename=file.filename or "unknown",
        file_type=file_type,
        original_text=extracted_text,
        page_count=page_count,
        status="pending",
        check_types=enabled_check_types,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    # Schedule Celery task for document checking
    enqueue_document_check(document.id)

    logger.info(f"Document uploaded: {document.id} ({file_type}, {page_count} pages)")

    return DocumentCheckUploadResponse(
        id=document.id,
        filename=document.filename,
        file_type=document.file_type,
        status=document.status,
        message="ドキュメントのチェックを開始しました",
    )


@router.get("/documents", response_model=DocumentCheckListResponse)
async def list_documents(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List user's document check history."""
    query = db.query(DocumentCheck).filter(DocumentCheck.user_id == current_user.id)

    if status_filter:
        query = query.filter(DocumentCheck.status == status_filter)

    total = query.count()

    documents = (
        query.order_by(DocumentCheck.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = []
    for doc in documents:
        # Count issues by severity
        issue_counts = (
            db.query(
                DocumentCheckIssue.severity,
                func.count(DocumentCheckIssue.id),
            )
            .filter(DocumentCheckIssue.document_id == doc.id)
            .group_by(DocumentCheckIssue.severity)
            .all()
        )

        error_count = 0
        warning_count = 0
        info_count = 0
        for severity, count in issue_counts:
            if severity == "error":
                error_count = count
            elif severity == "warning":
                warning_count = count
            elif severity == "info":
                info_count = count

        items.append(
            DocumentCheckSummary(
                id=doc.id,
                filename=doc.filename,
                file_type=doc.file_type,
                status=doc.status,
                issue_count=error_count + warning_count + info_count,
                error_count=error_count,
                warning_count=warning_count,
                info_count=info_count,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
            )
        )

    return DocumentCheckListResponse(
        items=items,
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/documents/{document_id}", response_model=DocumentCheckDetail)
async def get_document_result(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get detailed document check result."""
    try:
        doc_uuid = UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無効なドキュメントIDです",
        )

    document = db.query(DocumentCheck).filter(DocumentCheck.id == doc_uuid).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ドキュメントが見つかりません",
        )

    if document.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="このドキュメントにアクセスする権限がありません",
        )

    # Get issues
    issues = (
        db.query(DocumentCheckIssue)
        .filter(DocumentCheckIssue.document_id == doc_uuid)
        .order_by(DocumentCheckIssue.created_at)
        .all()
    )

    # Count by severity
    error_count = sum(1 for i in issues if i.severity == "error")
    warning_count = sum(1 for i in issues if i.severity == "warning")
    info_count = sum(1 for i in issues if i.severity == "info")

    return DocumentCheckDetail(
        id=document.id,
        filename=document.filename,
        file_type=document.file_type,
        original_text=document.original_text,
        page_count=document.page_count,
        status=document.status,
        error_message=document.error_message,
        check_types=document.check_types or [],
        issues=[DocumentCheckIssueOut.model_validate(i) for i in issues],
        issue_count=len(issues),
        error_count=error_count,
        warning_count=warning_count,
        info_count=info_count,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a document check record."""
    try:
        doc_uuid = UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無効なドキュメントIDです",
        )

    document = db.query(DocumentCheck).filter(DocumentCheck.id == doc_uuid).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ドキュメントが見つかりません",
        )

    if document.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="このドキュメントを削除する権限がありません",
        )

    db.delete(document)
    db.commit()

    logger.info(f"Document deleted: {document_id}")


@router.patch("/issues/{issue_id}", response_model=IssueUpdateResponse)
async def update_issue_status(
    issue_id: str,
    request: IssueUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an issue's acceptance status."""
    try:
        issue_uuid = UUID(issue_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無効な問題IDです",
        )

    issue = (
        db.query(DocumentCheckIssue).filter(DocumentCheckIssue.id == issue_uuid).first()
    )
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="問題が見つかりません",
        )

    # Check ownership via document
    document = (
        db.query(DocumentCheck).filter(DocumentCheck.id == issue.document_id).first()
    )
    if not document or document.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="この問題を更新する権限がありません",
        )

    issue.is_accepted = request.is_accepted
    db.commit()

    return IssueUpdateResponse(
        id=issue.id,
        is_accepted=issue.is_accepted,
        message="問題のステータスを更新しました",
    )


@router.get("/preferences", response_model=UserCheckPreferenceOut)
async def get_user_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get user's default check preferences."""
    preference = (
        db.query(UserCheckPreference)
        .filter(UserCheckPreference.user_id == current_user.id)
        .first()
    )

    if not preference:
        # Return defaults
        return UserCheckPreferenceOut(
            default_check_types=get_default_check_types(),
            custom_terminology=None,
        )

    return UserCheckPreferenceOut(
        default_check_types=preference.default_check_types or get_default_check_types(),
        custom_terminology=preference.custom_terminology,
    )


@router.put("/preferences", response_model=UserCheckPreferenceOut)
async def update_user_preferences(
    request: UserCheckPreferenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update user's default check preferences."""
    preference = (
        db.query(UserCheckPreference)
        .filter(UserCheckPreference.user_id == current_user.id)
        .first()
    )

    if not preference:
        preference = UserCheckPreference(user_id=current_user.id)
        db.add(preference)

    if request.default_check_types is not None:
        # Validate check types
        valid_types = [ct for ct in request.default_check_types if ct in CHECK_TYPES]
        preference.default_check_types = valid_types

    if request.custom_terminology is not None:
        preference.custom_terminology = request.custom_terminology

    db.commit()
    db.refresh(preference)

    return UserCheckPreferenceOut(
        default_check_types=preference.default_check_types or get_default_check_types(),
        custom_terminology=preference.custom_terminology,
    )
