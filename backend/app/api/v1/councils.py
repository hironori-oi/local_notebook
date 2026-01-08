"""
Council management API endpoints.

Provides CRUD operations for councils (審議会) and calendar view.
"""
from typing import List, Literal
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user, check_council_access, parse_uuid
from app.models.council import Council
from app.models.council_meeting import CouncilMeeting
from app.models.council_agenda_item import CouncilAgendaItem
from app.models.council_note import CouncilNote
from app.models.user import User
from app.schemas.council import (
    CouncilCreate,
    CouncilUpdate,
    CouncilOut,
    CouncilListOut,
    CouncilDetailOut,
)
from app.schemas.council_meeting import (
    CalendarResponse,
    CalendarMeetingItem,
    GlobalCalendarResponse,
    GlobalCalendarMeetingItem,
)
from app.services.audit import log_action, get_client_info, AuditAction, TargetType

router = APIRouter(prefix="/councils", tags=["councils"])


@router.get("", response_model=List[CouncilListOut])
def list_councils(
    filter_type: Literal["all", "mine", "public"] = Query(
        "all", description="Filter type: all (mine + public), mine (only mine), public (only public)"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List councils based on filter type.

    - all: All councils the user can access (own + public)
    - mine: Only councils owned by the user
    - public: Only public councils
    """
    # Build meeting count subquery
    meeting_count_subq = (
        db.query(
            CouncilMeeting.council_id,
            func.count(CouncilMeeting.id).label("meeting_count")
        )
        .group_by(CouncilMeeting.council_id)
        .subquery()
    )

    query = (
        db.query(
            Council.id,
            Council.title,
            Council.description,
            Council.organization,
            Council.council_type,
            Council.official_url,
            Council.is_public,
            Council.owner_id,
            User.display_name.label("owner_display_name"),
            func.coalesce(meeting_count_subq.c.meeting_count, 0).label("meeting_count"),
            Council.created_at,
            Council.updated_at,
        )
        .join(User, Council.owner_id == User.id)
        .outerjoin(meeting_count_subq, Council.id == meeting_count_subq.c.council_id)
    )

    if filter_type == "mine":
        query = query.filter(Council.owner_id == current_user.id)
    elif filter_type == "public":
        query = query.filter(Council.is_public == True)
    else:  # "all"
        query = query.filter(
            or_(
                Council.owner_id == current_user.id,
                Council.is_public == True
            )
        )

    query = query.order_by(Council.updated_at.desc())
    results = query.all()

    councils = []
    for row in results:
        councils.append(CouncilListOut(
            id=row.id,
            title=row.title,
            description=row.description,
            organization=row.organization,
            council_type=row.council_type,
            official_url=row.official_url,
            is_public=row.is_public,
            owner_id=row.owner_id,
            owner_display_name=row.owner_display_name,
            meeting_count=row.meeting_count,
            created_at=row.created_at,
            updated_at=row.updated_at,
        ))

    return councils


@router.get("/calendar", response_model=GlobalCalendarResponse)
def get_global_calendar(
    view: Literal["week", "month"] = Query("month", description="Calendar view type"),
    date: str = Query(None, description="Reference date (YYYY-MM-DD). Defaults to today."),
    filter_type: Literal["all", "mine", "public"] = Query(
        "all", description="Filter type: all, mine, or public"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get global calendar data for all accessible councils.

    Returns meetings from all councils within the specified view range (week or month).
    """
    # Parse reference date
    if date:
        try:
            ref_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="無効な日付形式です。YYYY-MM-DD形式で指定してください。",
            )
    else:
        ref_date = datetime.now()

    # Calculate date range based on view
    if view == "week":
        # Start from Sunday of the week
        start_date = ref_date - timedelta(days=ref_date.weekday() + 1)
        if ref_date.weekday() == 6:  # If Sunday, start from today
            start_date = ref_date
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=7)
    else:  # month
        # Start from first day of month
        start_date = ref_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # End at last day of month
        if ref_date.month == 12:
            end_date = start_date.replace(year=ref_date.year + 1, month=1)
        else:
            end_date = start_date.replace(month=ref_date.month + 1)

    # Build council filter
    if filter_type == "mine":
        council_filter = Council.owner_id == current_user.id
    elif filter_type == "public":
        council_filter = Council.is_public == True
    else:  # "all"
        council_filter = or_(
            Council.owner_id == current_user.id,
            Council.is_public == True
        )

    # Build agenda count subquery
    agenda_count_subq = (
        db.query(
            CouncilAgendaItem.meeting_id,
            func.count(CouncilAgendaItem.id).label("agenda_count")
        )
        .group_by(CouncilAgendaItem.meeting_id)
        .subquery()
    )

    # Query meetings with council info and agenda count
    meetings_query = (
        db.query(
            CouncilMeeting.id,
            CouncilMeeting.council_id,
            Council.title.label("council_title"),
            Council.organization.label("council_organization"),
            CouncilMeeting.meeting_number,
            CouncilMeeting.title,
            CouncilMeeting.scheduled_at,
            func.coalesce(agenda_count_subq.c.agenda_count, 0).label("agenda_count"),
        )
        .join(Council, CouncilMeeting.council_id == Council.id)
        .outerjoin(agenda_count_subq, CouncilMeeting.id == agenda_count_subq.c.meeting_id)
        .filter(
            council_filter,
            CouncilMeeting.scheduled_at >= start_date,
            CouncilMeeting.scheduled_at < end_date,
        )
        .order_by(CouncilMeeting.scheduled_at)
    )

    results = meetings_query.all()

    # Get unique council count
    council_ids = set(row.council_id for row in results)

    meeting_items = [
        GlobalCalendarMeetingItem(
            id=row.id,
            council_id=row.council_id,
            council_title=row.council_title,
            council_organization=row.council_organization,
            meeting_number=row.meeting_number,
            title=row.title,
            scheduled_at=row.scheduled_at,
            agenda_count=row.agenda_count,
        )
        for row in results
    ]

    return GlobalCalendarResponse(
        view=view,
        start_date=start_date,
        end_date=end_date,
        meetings=meeting_items,
        council_count=len(council_ids),
    )


@router.get("/{council_id}", response_model=CouncilDetailOut)
def get_council(
    council_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific council by ID with details.
    """
    council_uuid = parse_uuid(council_id, "審議会ID")
    council = check_council_access(db, council_uuid, current_user)

    # Get counts
    meeting_count = db.query(func.count(CouncilMeeting.id)).filter(
        CouncilMeeting.council_id == council.id
    ).scalar()

    note_count = db.query(func.count(CouncilNote.id)).filter(
        CouncilNote.council_id == council.id
    ).scalar()

    # Get owner display name
    owner = db.query(User).filter(User.id == council.owner_id).first()

    return CouncilDetailOut(
        id=council.id,
        title=council.title,
        description=council.description,
        organization=council.organization,
        council_type=council.council_type,
        official_url=council.official_url,
        is_public=council.is_public,
        owner_id=council.owner_id,
        owner_display_name=owner.display_name if owner else "Unknown",
        meeting_count=meeting_count or 0,
        note_count=note_count or 0,
        created_at=council.created_at,
        updated_at=council.updated_at,
    )


@router.post("", response_model=CouncilOut, status_code=status.HTTP_201_CREATED)
def create_council(
    data: CouncilCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new council.
    """
    ip_address, user_agent = get_client_info(request)

    council = Council(
        owner_id=current_user.id,
        title=data.title,
        description=data.description,
        organization=data.organization,
        council_type=data.council_type,
        official_url=data.official_url,
        is_public=True,  # 審議会は常に公開
    )
    db.add(council)
    db.commit()
    db.refresh(council)

    log_action(
        db=db,
        action=AuditAction.CREATE_COUNCIL,
        user_id=current_user.id,
        target_type=TargetType.COUNCIL,
        target_id=str(council.id),
        details={"title": council.title},
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return council


@router.patch("/{council_id}", response_model=CouncilOut)
def update_council(
    council_id: str,
    data: CouncilUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a council.

    審議会は常に公開のため、誰でも編集可能。
    """
    ip_address, user_agent = get_client_info(request)
    council_uuid = parse_uuid(council_id, "審議会ID")

    council = check_council_access(db, council_uuid, current_user)

    update_details = {}

    if data.title is not None:
        council.title = data.title
        update_details["title"] = data.title

    if data.description is not None:
        council.description = data.description
        update_details["description"] = data.description

    if data.organization is not None:
        council.organization = data.organization
        update_details["organization"] = data.organization

    if data.council_type is not None:
        council.council_type = data.council_type
        update_details["council_type"] = data.council_type

    if data.official_url is not None:
        council.official_url = data.official_url
        update_details["official_url"] = data.official_url

    # is_public は常にTrue（審議会は公開専用）

    db.commit()
    db.refresh(council)

    if update_details:
        log_action(
            db=db,
            action=AuditAction.UPDATE_COUNCIL,
            user_id=current_user.id,
            target_type=TargetType.COUNCIL,
            target_id=council_id,
            details=update_details,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    return council


@router.delete("/{council_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_council(
    council_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a council and all associated meetings, notes, and chat sessions.

    Only the owner can delete a council.
    """
    ip_address, user_agent = get_client_info(request)
    council_uuid = parse_uuid(council_id, "審議会ID")

    council = check_council_access(db, council_uuid, current_user, require_owner=True)
    council_title = council.title

    db.delete(council)
    db.commit()

    log_action(
        db=db,
        action=AuditAction.DELETE_COUNCIL,
        user_id=current_user.id,
        target_type=TargetType.COUNCIL,
        target_id=council_id,
        details={"title": council_title},
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return None


@router.get("/{council_id}/calendar", response_model=CalendarResponse)
def get_council_calendar(
    council_id: str,
    view: Literal["week", "month"] = Query("month", description="Calendar view type"),
    date: str = Query(None, description="Reference date (YYYY-MM-DD). Defaults to today."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get calendar data for a council.

    Returns meetings within the specified view range (week or month).
    """
    council_uuid = parse_uuid(council_id, "審議会ID")
    check_council_access(db, council_uuid, current_user)

    # Parse reference date
    if date:
        try:
            ref_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="無効な日付形式です。YYYY-MM-DD形式で指定してください。",
            )
    else:
        ref_date = datetime.now()

    # Calculate date range based on view
    if view == "week":
        # Start from Monday of the week
        start_date = ref_date - timedelta(days=ref_date.weekday())
        end_date = start_date + timedelta(days=7)
    else:  # month
        # Start from first day of month
        start_date = ref_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # End at last day of month
        if ref_date.month == 12:
            end_date = start_date.replace(year=ref_date.year + 1, month=1)
        else:
            end_date = start_date.replace(month=ref_date.month + 1)

    # Build agenda count subquery for calendar
    agenda_count_subq = (
        db.query(
            CouncilAgendaItem.meeting_id,
            func.count(CouncilAgendaItem.id).label("agenda_count")
        )
        .group_by(CouncilAgendaItem.meeting_id)
        .subquery()
    )

    # Query meetings within range
    results = (
        db.query(
            CouncilMeeting.id,
            CouncilMeeting.meeting_number,
            CouncilMeeting.title,
            CouncilMeeting.scheduled_at,
            func.coalesce(agenda_count_subq.c.agenda_count, 0).label("agenda_count"),
        )
        .outerjoin(agenda_count_subq, CouncilMeeting.id == agenda_count_subq.c.meeting_id)
        .filter(
            CouncilMeeting.council_id == council_uuid,
            CouncilMeeting.scheduled_at >= start_date,
            CouncilMeeting.scheduled_at < end_date,
        )
        .order_by(CouncilMeeting.scheduled_at)
        .all()
    )

    meeting_items = [
        CalendarMeetingItem(
            id=row.id,
            meeting_number=row.meeting_number,
            title=row.title,
            scheduled_at=row.scheduled_at,
            agenda_count=row.agenda_count,
        )
        for row in results
    ]

    return CalendarResponse(
        council_id=council_uuid,
        view=view,
        start_date=start_date,
        end_date=end_date,
        meetings=meeting_items,
    )
