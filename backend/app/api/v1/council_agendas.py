"""
Council agenda item management API endpoints.

Provides CRUD operations for council agenda items (議題) with URL processing.
"""

from typing import List, Literal
from uuid import UUID

import logging
import uuid
from pathlib import Path

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

from app.core.config import settings
from app.services.file_validator import FileValidationError, validate_uploaded_file
from app.services.storage import get_storage_service

logger = logging.getLogger(__name__)

from app.celery_app.tasks.council import (
    enqueue_agenda_content_processing,
    enqueue_agenda_summary_regeneration,
)
from app.core.deps import check_council_access, get_current_user, get_db, parse_uuid
from app.models.council_agenda_item import CouncilAgendaItem
from app.models.council_agenda_material import CouncilAgendaMaterial
from app.models.council_meeting import CouncilMeeting
from app.models.user import User
from app.schemas.council_agenda import (
    CouncilAgendaCreate,
    CouncilAgendaDetailOut,
    CouncilAgendaListItem,
    CouncilAgendaMaterialCreate,
    CouncilAgendaMaterialDetailOut,
    CouncilAgendaMaterialOut,
    CouncilAgendaMaterialSummaryUpdate,
    CouncilAgendaMaterialUpdate,
    CouncilAgendaOut,
    CouncilAgendaSummaryUpdate,
    CouncilAgendaUpdate,
)
from app.services.audit import AuditAction, TargetType, get_client_info, log_action

router = APIRouter(prefix="/council-agendas", tags=["council-agendas"])


def _build_material_out(material: CouncilAgendaMaterial) -> CouncilAgendaMaterialOut:
    """Build material output schema."""
    return CouncilAgendaMaterialOut(
        id=material.id,
        agenda_id=material.agenda_id,
        material_number=material.material_number,
        title=material.title,
        source_type=material.source_type,
        url=material.url,
        original_filename=material.original_filename,
        processing_status=material.processing_status,
        has_summary=bool(material.summary),
        created_at=material.created_at,
        updated_at=material.updated_at,
    )


def _build_material_detail_out(
    material: CouncilAgendaMaterial,
) -> CouncilAgendaMaterialDetailOut:
    """Build material detail output schema."""
    return CouncilAgendaMaterialDetailOut(
        id=material.id,
        agenda_id=material.agenda_id,
        material_number=material.material_number,
        title=material.title,
        source_type=material.source_type,
        url=material.url,
        original_filename=material.original_filename,
        processing_status=material.processing_status,
        has_summary=bool(material.summary),
        text=material.text,
        summary=material.summary,
        processing_error=material.processing_error,
        created_at=material.created_at,
        updated_at=material.updated_at,
    )


def _get_meeting_and_check_access(
    db: Session, meeting_id: UUID, current_user: User
) -> CouncilMeeting:
    """Get meeting and check access."""
    meeting = db.query(CouncilMeeting).filter(CouncilMeeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="開催回が見つかりません",
        )
    check_council_access(db, meeting.council_id, current_user)
    return meeting


def _get_agenda_and_check_access(
    db: Session, agenda_id: UUID, current_user: User
) -> CouncilAgendaItem:
    """Get agenda and check access."""
    agenda = (
        db.query(CouncilAgendaItem).filter(CouncilAgendaItem.id == agenda_id).first()
    )
    if not agenda:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="議題が見つかりません",
        )
    meeting = (
        db.query(CouncilMeeting).filter(CouncilMeeting.id == agenda.meeting_id).first()
    )
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="開催回が見つかりません",
        )
    check_council_access(db, meeting.council_id, current_user)
    return agenda


def _get_aggregated_materials_status(agenda: CouncilAgendaItem) -> str:
    """Get aggregated processing status from materials array."""
    if not agenda.materials or len(agenda.materials) == 0:
        # No materials in array, use legacy status
        return agenda.materials_processing_status

    statuses = [m.processing_status for m in agenda.materials]
    if any(s == "failed" for s in statuses):
        return "failed"
    if any(s == "processing" for s in statuses):
        return "processing"
    if any(s == "pending" for s in statuses):
        return "pending"
    if all(s == "completed" for s in statuses):
        return "completed"
    return "completed"


@router.get("/meeting/{meeting_id}", response_model=List[CouncilAgendaListItem])
def list_meeting_agendas(
    meeting_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all agenda items for a meeting.
    """
    meeting_uuid = parse_uuid(meeting_id, "meeting ID")
    _get_meeting_and_check_access(db, meeting_uuid, current_user)

    agendas = (
        db.query(CouncilAgendaItem)
        .filter(CouncilAgendaItem.meeting_id == meeting_uuid)
        .order_by(CouncilAgendaItem.agenda_number)
        .all()
    )

    return [
        CouncilAgendaListItem(
            id=agenda.id,
            meeting_id=agenda.meeting_id,
            agenda_number=agenda.agenda_number,
            title=agenda.title,
            has_materials_url=bool(agenda.materials_url),
            has_minutes_url=bool(agenda.minutes_url),
            materials_processing_status=_get_aggregated_materials_status(agenda),
            minutes_processing_status=agenda.minutes_processing_status,
            has_materials_summary=bool(agenda.materials_summary)
            or any(m.summary for m in agenda.materials if agenda.materials),
            has_minutes_summary=bool(agenda.minutes_summary),
            materials_count=len(agenda.materials) if agenda.materials else 0,
            created_at=agenda.created_at,
            updated_at=agenda.updated_at,
        )
        for agenda in agendas
    ]


@router.get("/{agenda_id}", response_model=CouncilAgendaOut)
def get_agenda(
    agenda_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific agenda item by ID.
    """
    agenda_uuid = parse_uuid(agenda_id, "agenda ID")
    agenda = _get_agenda_and_check_access(db, agenda_uuid, current_user)

    return CouncilAgendaOut(
        id=agenda.id,
        meeting_id=agenda.meeting_id,
        agenda_number=agenda.agenda_number,
        title=agenda.title,
        materials_url=agenda.materials_url,
        minutes_url=agenda.minutes_url,
        materials_processing_status=agenda.materials_processing_status,
        minutes_processing_status=agenda.minutes_processing_status,
        has_materials_summary=bool(agenda.materials_summary),
        has_minutes_summary=bool(agenda.minutes_summary),
        materials_count=len(agenda.materials) if agenda.materials else 0,
        materials=(
            [_build_material_out(m) for m in agenda.materials]
            if agenda.materials
            else []
        ),
        created_at=agenda.created_at,
        updated_at=agenda.updated_at,
    )


@router.get("/{agenda_id}/detail", response_model=CouncilAgendaDetailOut)
def get_agenda_detail(
    agenda_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get detailed information for an agenda item, including summaries and text.
    """
    agenda_uuid = parse_uuid(agenda_id, "agenda ID")
    agenda = _get_agenda_and_check_access(db, agenda_uuid, current_user)

    return CouncilAgendaDetailOut(
        id=agenda.id,
        meeting_id=agenda.meeting_id,
        agenda_number=agenda.agenda_number,
        title=agenda.title,
        materials_url=agenda.materials_url,
        minutes_url=agenda.minutes_url,
        materials_text=agenda.materials_text,
        minutes_text=agenda.minutes_text,
        materials_summary=agenda.materials_summary,
        minutes_summary=agenda.minutes_summary,
        materials_processing_status=agenda.materials_processing_status,
        minutes_processing_status=agenda.minutes_processing_status,
        has_materials_summary=bool(agenda.materials_summary),
        has_minutes_summary=bool(agenda.minutes_summary),
        processing_error=agenda.processing_error,
        materials_count=len(agenda.materials) if agenda.materials else 0,
        materials=(
            [_build_material_detail_out(m) for m in agenda.materials]
            if agenda.materials
            else []
        ),
        created_at=agenda.created_at,
        updated_at=agenda.updated_at,
    )


@router.post(
    "/meeting/{meeting_id}",
    response_model=CouncilAgendaOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_agenda(
    meeting_id: str,
    data: CouncilAgendaCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new agenda item for a meeting.

    If materials_url or minutes_url is provided, background processing will be triggered.
    """
    ip_address, user_agent = get_client_info(request)
    meeting_uuid = parse_uuid(meeting_id, "meeting ID")
    meeting = _get_meeting_and_check_access(db, meeting_uuid, current_user)

    # Check if agenda number already exists for this meeting
    existing = (
        db.query(CouncilAgendaItem)
        .filter(
            CouncilAgendaItem.meeting_id == meeting_uuid,
            CouncilAgendaItem.agenda_number == data.agenda_number,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Agenda number {data.agenda_number} already exists for this meeting",
        )

    agenda = CouncilAgendaItem(
        meeting_id=meeting_uuid,
        agenda_number=data.agenda_number,
        title=data.title,
        materials_url=data.materials_url,
        minutes_url=data.minutes_url,
        materials_processing_status="pending",
        minutes_processing_status="pending",
    )
    db.add(agenda)
    db.commit()
    db.refresh(agenda)

    # Create materials if provided
    created_materials = []
    if data.materials:
        for mat_data in data.materials:
            material = CouncilAgendaMaterial(
                agenda_id=agenda.id,
                material_number=mat_data.material_number,
                title=mat_data.title,
                url=mat_data.url,
                processing_status="pending",
            )
            db.add(material)
            created_materials.append(material)
        db.commit()
        for mat in created_materials:
            db.refresh(mat)

    # Trigger background processing if URLs are provided
    has_materials_to_process = data.materials_url or (
        data.materials and len(data.materials) > 0
    )
    if has_materials_to_process or data.minutes_url:
        enqueue_agenda_content_processing(agenda.id)

    log_action(
        db=db,
        action=AuditAction.CREATE_COUNCIL_MEETING,  # Reuse meeting action type
        user_id=current_user.id,
        target_type=TargetType.COUNCIL_MEETING,
        target_id=str(agenda.id),
        details={
            "meeting_id": meeting_id,
            "agenda_number": agenda.agenda_number,
            "title": agenda.title,
            "materials_count": len(created_materials),
            "type": "agenda_item",
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return CouncilAgendaOut(
        id=agenda.id,
        meeting_id=agenda.meeting_id,
        agenda_number=agenda.agenda_number,
        title=agenda.title,
        materials_url=agenda.materials_url,
        minutes_url=agenda.minutes_url,
        materials_processing_status=agenda.materials_processing_status,
        minutes_processing_status=agenda.minutes_processing_status,
        has_materials_summary=False,
        has_minutes_summary=False,
        materials_count=len(created_materials),
        materials=[_build_material_out(m) for m in created_materials],
        created_at=agenda.created_at,
        updated_at=agenda.updated_at,
    )


@router.patch("/{agenda_id}", response_model=CouncilAgendaOut)
async def update_agenda(
    agenda_id: str,
    data: CouncilAgendaUpdate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update an agenda item.

    If materials_url or minutes_url is changed, background processing will be triggered.
    """
    ip_address, user_agent = get_client_info(request)
    agenda_uuid = parse_uuid(agenda_id, "agenda ID")
    agenda = _get_agenda_and_check_access(db, agenda_uuid, current_user)

    update_details = {}
    urls_changed = False

    if data.agenda_number is not None and data.agenda_number != agenda.agenda_number:
        # Check if new number already exists
        existing = (
            db.query(CouncilAgendaItem)
            .filter(
                CouncilAgendaItem.meeting_id == agenda.meeting_id,
                CouncilAgendaItem.agenda_number == data.agenda_number,
                CouncilAgendaItem.id != agenda.id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Agenda number {data.agenda_number} already exists for this meeting",
            )
        agenda.agenda_number = data.agenda_number
        update_details["agenda_number"] = data.agenda_number

    if data.title is not None:
        agenda.title = data.title
        update_details["title"] = data.title

    if data.materials_url is not None and data.materials_url != agenda.materials_url:
        agenda.materials_url = data.materials_url
        agenda.materials_processing_status = "pending"
        agenda.materials_text = None
        agenda.materials_summary = None
        update_details["materials_url"] = data.materials_url
        urls_changed = True

    if data.minutes_url is not None and data.minutes_url != agenda.minutes_url:
        agenda.minutes_url = data.minutes_url
        agenda.minutes_processing_status = "pending"
        agenda.minutes_text = None
        agenda.minutes_summary = None
        update_details["minutes_url"] = data.minutes_url
        urls_changed = True

    db.commit()
    db.refresh(agenda)

    # Trigger background processing if URLs changed
    if urls_changed:
        enqueue_agenda_content_processing(agenda.id)

    if update_details:
        log_action(
            db=db,
            action=AuditAction.UPDATE_COUNCIL_MEETING,
            user_id=current_user.id,
            target_type=TargetType.COUNCIL_MEETING,
            target_id=agenda_id,
            details={**update_details, "type": "agenda_item"},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    return CouncilAgendaOut(
        id=agenda.id,
        meeting_id=agenda.meeting_id,
        agenda_number=agenda.agenda_number,
        title=agenda.title,
        materials_url=agenda.materials_url,
        minutes_url=agenda.minutes_url,
        materials_processing_status=agenda.materials_processing_status,
        minutes_processing_status=agenda.minutes_processing_status,
        has_materials_summary=bool(agenda.materials_summary),
        has_minutes_summary=bool(agenda.minutes_summary),
        materials_count=len(agenda.materials) if agenda.materials else 0,
        materials=(
            [_build_material_out(m) for m in agenda.materials]
            if agenda.materials
            else []
        ),
        created_at=agenda.created_at,
        updated_at=agenda.updated_at,
    )


@router.delete("/{agenda_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agenda(
    agenda_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete an agenda item and all associated chunks.
    """
    ip_address, user_agent = get_client_info(request)
    agenda_uuid = parse_uuid(agenda_id, "agenda ID")
    agenda = _get_agenda_and_check_access(db, agenda_uuid, current_user)

    # Check council owner access
    meeting = (
        db.query(CouncilMeeting).filter(CouncilMeeting.id == agenda.meeting_id).first()
    )
    check_council_access(db, meeting.council_id, current_user, require_owner=True)

    agenda_number = agenda.agenda_number
    meeting_id = str(agenda.meeting_id)

    db.delete(agenda)
    db.commit()

    log_action(
        db=db,
        action=AuditAction.DELETE_COUNCIL_MEETING,
        user_id=current_user.id,
        target_type=TargetType.COUNCIL_MEETING,
        target_id=agenda_id,
        details={
            "meeting_id": meeting_id,
            "agenda_number": agenda_number,
            "type": "agenda_item",
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return None


@router.post("/{agenda_id}/regenerate", response_model=CouncilAgendaOut)
async def regenerate_agenda_summary(
    agenda_id: str,
    content_type: Literal["materials", "minutes", "both"] = Query(
        "both", description="Which summaries to regenerate"
    ),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Regenerate summaries for an agenda item.

    This will re-fetch content from URLs and regenerate summaries.
    """
    agenda_uuid = parse_uuid(agenda_id, "agenda ID")
    agenda = _get_agenda_and_check_access(db, agenda_uuid, current_user)

    # Check if there's content to regenerate
    can_regenerate_materials = bool(agenda.materials_url)
    can_regenerate_minutes = bool(agenda.minutes_url)

    if content_type == "materials" and not can_regenerate_materials:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="資料URLが登録されていません",
        )

    if content_type == "minutes" and not can_regenerate_minutes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="議事録URLが登録されていません",
        )

    if (
        content_type == "both"
        and not can_regenerate_materials
        and not can_regenerate_minutes
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="資料または議事録URLが登録されていません",
        )

    # Determine what to actually regenerate
    actual_content_type = content_type
    if content_type == "both":
        if can_regenerate_materials and not can_regenerate_minutes:
            actual_content_type = "materials"
        elif can_regenerate_minutes and not can_regenerate_materials:
            actual_content_type = "minutes"

    # Update status to processing
    if actual_content_type in ("materials", "both") and can_regenerate_materials:
        agenda.materials_processing_status = "processing"
    if actual_content_type in ("minutes", "both") and can_regenerate_minutes:
        agenda.minutes_processing_status = "processing"
    db.commit()

    # Trigger background regeneration
    enqueue_agenda_summary_regeneration(agenda.id, actual_content_type)

    db.refresh(agenda)

    return CouncilAgendaOut(
        id=agenda.id,
        meeting_id=agenda.meeting_id,
        agenda_number=agenda.agenda_number,
        title=agenda.title,
        materials_url=agenda.materials_url,
        minutes_url=agenda.minutes_url,
        materials_processing_status=agenda.materials_processing_status,
        minutes_processing_status=agenda.minutes_processing_status,
        has_materials_summary=bool(agenda.materials_summary),
        has_minutes_summary=bool(agenda.minutes_summary),
        materials_count=len(agenda.materials) if agenda.materials else 0,
        materials=(
            [_build_material_out(m) for m in agenda.materials]
            if agenda.materials
            else []
        ),
        created_at=agenda.created_at,
        updated_at=agenda.updated_at,
    )


@router.patch("/{agenda_id}/summary", response_model=CouncilAgendaOut)
def update_agenda_summary(
    agenda_id: str,
    data: CouncilAgendaSummaryUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Manually update agenda summaries.
    """
    ip_address, user_agent = get_client_info(request)
    agenda_uuid = parse_uuid(agenda_id, "agenda ID")
    agenda = _get_agenda_and_check_access(db, agenda_uuid, current_user)

    update_details = {}

    if data.materials_summary is not None:
        agenda.materials_summary = data.materials_summary
        update_details["materials_summary_updated"] = True

    if data.minutes_summary is not None:
        agenda.minutes_summary = data.minutes_summary
        update_details["minutes_summary_updated"] = True

    db.commit()
    db.refresh(agenda)

    if update_details:
        log_action(
            db=db,
            action=AuditAction.UPDATE_COUNCIL_MEETING,
            user_id=current_user.id,
            target_type=TargetType.COUNCIL_MEETING,
            target_id=agenda_id,
            details={**update_details, "type": "agenda_item"},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    return CouncilAgendaOut(
        id=agenda.id,
        meeting_id=agenda.meeting_id,
        agenda_number=agenda.agenda_number,
        title=agenda.title,
        materials_url=agenda.materials_url,
        minutes_url=agenda.minutes_url,
        materials_processing_status=agenda.materials_processing_status,
        minutes_processing_status=agenda.minutes_processing_status,
        has_materials_summary=bool(agenda.materials_summary),
        has_minutes_summary=bool(agenda.minutes_summary),
        materials_count=len(agenda.materials) if agenda.materials else 0,
        materials=(
            [_build_material_out(m) for m in agenda.materials]
            if agenda.materials
            else []
        ),
        created_at=agenda.created_at,
        updated_at=agenda.updated_at,
    )


# =============================================================================
# Material CRUD endpoints
# =============================================================================


@router.get("/{agenda_id}/materials", response_model=List[CouncilAgendaMaterialOut])
def list_agenda_materials(
    agenda_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all materials for an agenda item.
    """
    agenda_uuid = parse_uuid(agenda_id, "agenda ID")
    agenda = _get_agenda_and_check_access(db, agenda_uuid, current_user)

    return (
        [_build_material_out(m) for m in agenda.materials] if agenda.materials else []
    )


@router.post(
    "/{agenda_id}/materials",
    response_model=CouncilAgendaMaterialOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_agenda_material(
    agenda_id: str,
    data: CouncilAgendaMaterialCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Add a new material to an agenda item.
    """
    ip_address, user_agent = get_client_info(request)
    agenda_uuid = parse_uuid(agenda_id, "agenda ID")
    agenda = _get_agenda_and_check_access(db, agenda_uuid, current_user)

    # Check if material number already exists for this agenda
    existing = (
        db.query(CouncilAgendaMaterial)
        .filter(
            CouncilAgendaMaterial.agenda_id == agenda_uuid,
            CouncilAgendaMaterial.material_number == data.material_number,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"資料番号 {data.material_number} は既に登録されています",
        )

    material = CouncilAgendaMaterial(
        agenda_id=agenda_uuid,
        material_number=data.material_number,
        title=data.title,
        url=data.url,
        processing_status="pending",
    )
    db.add(material)
    db.commit()
    db.refresh(material)

    # Trigger background processing
    enqueue_agenda_content_processing(agenda.id)

    log_action(
        db=db,
        action=AuditAction.CREATE_COUNCIL_MEETING,
        user_id=current_user.id,
        target_type=TargetType.COUNCIL_MEETING,
        target_id=str(material.id),
        details={
            "agenda_id": agenda_id,
            "material_number": material.material_number,
            "title": material.title,
            "type": "agenda_material",
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return _build_material_out(material)


@router.post(
    "/{agenda_id}/materials/upload",
    response_model=CouncilAgendaMaterialOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_agenda_material(
    agenda_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a PDF file as material for an agenda item.

    Supported file types: PDF
    Processing flow:
    1. File validation (extension, magic bytes, size)
    2. Save to storage
    3. Create DB record
    4. Background processing for text extraction and summary generation
    """
    ip_address, user_agent = get_client_info(request)
    agenda_uuid = parse_uuid(agenda_id, "agenda ID")
    agenda = _get_agenda_and_check_access(db, agenda_uuid, current_user)

    # Read file content
    content = await file.read()

    # Validate file (only PDF allowed for council materials)
    try:
        file_type = validate_uploaded_file(
            filename=file.filename or "",
            content=content,
            allowed_extensions={"pdf"},
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
    material_id = uuid.uuid4()
    suffix = Path(file.filename or "").suffix.lower()
    storage_path = f"council_materials/{agenda_id}/{material_id}{suffix}"

    # Save file to storage
    try:
        file_location = storage.upload(
            storage_path, content, file.content_type or "application/pdf"
        )
    except Exception as e:
        logger.error(f"Failed to write file to storage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ファイルの保存に失敗しました",
        )

    # Calculate next material number
    max_number = (
        db.query(CouncilAgendaMaterial.material_number)
        .filter(CouncilAgendaMaterial.agenda_id == agenda_uuid)
        .order_by(CouncilAgendaMaterial.material_number.desc())
        .first()
    )
    next_number = (max_number[0] + 1) if max_number else 1

    # Create material record
    material = CouncilAgendaMaterial(
        id=material_id,
        agenda_id=agenda_uuid,
        material_number=next_number,
        title=title or file.filename,
        source_type="file",
        url=None,
        file_path=storage_path,
        original_filename=file.filename,
        processing_status="pending",
    )

    try:
        db.add(material)
        db.commit()
        db.refresh(material)
    except Exception as e:
        # Rollback: delete the file if database insert fails
        logger.error(f"Database insert failed, rolling back file: {e}")
        try:
            storage.delete(storage_path)
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="資料の登録に失敗しました",
        )

    # Trigger background processing
    enqueue_agenda_content_processing(agenda.id)

    log_action(
        db=db,
        action=AuditAction.CREATE_COUNCIL_MEETING,
        user_id=current_user.id,
        target_type=TargetType.COUNCIL_MEETING,
        target_id=str(material.id),
        details={
            "agenda_id": agenda_id,
            "material_number": material.material_number,
            "title": material.title,
            "type": "agenda_material_upload",
            "filename": file.filename,
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return _build_material_out(material)


@router.get(
    "/{agenda_id}/materials/{material_id}",
    response_model=CouncilAgendaMaterialDetailOut,
)
def get_agenda_material(
    agenda_id: str,
    material_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get detailed information for a specific material.
    """
    agenda_uuid = parse_uuid(agenda_id, "agenda ID")
    material_uuid = parse_uuid(material_id, "material ID")
    _get_agenda_and_check_access(db, agenda_uuid, current_user)

    material = (
        db.query(CouncilAgendaMaterial)
        .filter(
            CouncilAgendaMaterial.id == material_uuid,
            CouncilAgendaMaterial.agenda_id == agenda_uuid,
        )
        .first()
    )
    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="資料が見つかりません",
        )

    return _build_material_detail_out(material)


@router.patch(
    "/{agenda_id}/materials/{material_id}", response_model=CouncilAgendaMaterialOut
)
async def update_agenda_material(
    agenda_id: str,
    material_id: str,
    data: CouncilAgendaMaterialUpdate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a material's information.
    """
    ip_address, user_agent = get_client_info(request)
    agenda_uuid = parse_uuid(agenda_id, "agenda ID")
    material_uuid = parse_uuid(material_id, "material ID")
    agenda = _get_agenda_and_check_access(db, agenda_uuid, current_user)

    material = (
        db.query(CouncilAgendaMaterial)
        .filter(
            CouncilAgendaMaterial.id == material_uuid,
            CouncilAgendaMaterial.agenda_id == agenda_uuid,
        )
        .first()
    )
    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="資料が見つかりません",
        )

    update_details = {}
    url_changed = False

    if (
        data.material_number is not None
        and data.material_number != material.material_number
    ):
        # Check if new number already exists
        existing = (
            db.query(CouncilAgendaMaterial)
            .filter(
                CouncilAgendaMaterial.agenda_id == agenda_uuid,
                CouncilAgendaMaterial.material_number == data.material_number,
                CouncilAgendaMaterial.id != material.id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"資料番号 {data.material_number} は既に登録されています",
            )
        material.material_number = data.material_number
        update_details["material_number"] = data.material_number

    if data.title is not None:
        material.title = data.title
        update_details["title"] = data.title

    if data.url is not None and data.url != material.url:
        material.url = data.url
        material.processing_status = "pending"
        material.text = None
        material.summary = None
        update_details["url"] = data.url
        url_changed = True

    db.commit()
    db.refresh(material)

    # Trigger background processing if URL changed
    if url_changed:
        enqueue_agenda_content_processing(agenda.id)

    if update_details:
        log_action(
            db=db,
            action=AuditAction.UPDATE_COUNCIL_MEETING,
            user_id=current_user.id,
            target_type=TargetType.COUNCIL_MEETING,
            target_id=material_id,
            details={**update_details, "type": "agenda_material"},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    return _build_material_out(material)


@router.delete(
    "/{agenda_id}/materials/{material_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_agenda_material(
    agenda_id: str,
    material_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a material from an agenda item.
    """
    ip_address, user_agent = get_client_info(request)
    agenda_uuid = parse_uuid(agenda_id, "agenda ID")
    material_uuid = parse_uuid(material_id, "material ID")

    # Check council owner access
    agenda = _get_agenda_and_check_access(db, agenda_uuid, current_user)
    meeting = (
        db.query(CouncilMeeting).filter(CouncilMeeting.id == agenda.meeting_id).first()
    )
    check_council_access(db, meeting.council_id, current_user, require_owner=True)

    material = (
        db.query(CouncilAgendaMaterial)
        .filter(
            CouncilAgendaMaterial.id == material_uuid,
            CouncilAgendaMaterial.agenda_id == agenda_uuid,
        )
        .first()
    )
    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="資料が見つかりません",
        )

    material_number = material.material_number
    file_path = material.file_path

    db.delete(material)
    db.commit()

    # Delete file from storage if this was an uploaded file
    if file_path:
        try:
            storage = get_storage_service("uploads")
            storage.delete(file_path)
        except Exception as e:
            logger.warning(f"Failed to delete file from storage: {e}")

    log_action(
        db=db,
        action=AuditAction.DELETE_COUNCIL_MEETING,
        user_id=current_user.id,
        target_type=TargetType.COUNCIL_MEETING,
        target_id=material_id,
        details={
            "agenda_id": agenda_id,
            "material_number": material_number,
            "type": "agenda_material",
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return None


@router.patch(
    "/{agenda_id}/materials/{material_id}/summary",
    response_model=CouncilAgendaMaterialOut,
)
def update_material_summary(
    agenda_id: str,
    material_id: str,
    data: CouncilAgendaMaterialSummaryUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Manually update a material's summary.
    """
    ip_address, user_agent = get_client_info(request)
    agenda_uuid = parse_uuid(agenda_id, "agenda ID")
    material_uuid = parse_uuid(material_id, "material ID")
    _get_agenda_and_check_access(db, agenda_uuid, current_user)

    material = (
        db.query(CouncilAgendaMaterial)
        .filter(
            CouncilAgendaMaterial.id == material_uuid,
            CouncilAgendaMaterial.agenda_id == agenda_uuid,
        )
        .first()
    )
    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="資料が見つかりません",
        )

    if data.summary is not None:
        material.summary = data.summary
        db.commit()
        db.refresh(material)

        log_action(
            db=db,
            action=AuditAction.UPDATE_COUNCIL_MEETING,
            user_id=current_user.id,
            target_type=TargetType.COUNCIL_MEETING,
            target_id=material_id,
            details={"summary_updated": True, "type": "agenda_material"},
            ip_address=ip_address,
            user_agent=user_agent,
        )

    return _build_material_out(material)
