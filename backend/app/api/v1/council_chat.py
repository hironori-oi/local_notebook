"""
Council chat API endpoints.

Provides chat functionality with RAG support for council meetings.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import check_council_access, get_current_user, get_db, parse_uuid
from app.models.council_chat_session import CouncilChatSession
from app.models.council_message import CouncilMessage
from app.models.user import User
from app.schemas.council_chat import (
    CouncilChatHistoryResponse,
    CouncilChatRequest,
    CouncilChatResponse,
    CouncilChatSessionCreate,
    CouncilChatSessionListResponse,
    CouncilChatSessionResponse,
    CouncilChatSessionUpdate,
    CouncilMessageOut,
)
from app.services.audit import AuditAction, TargetType, get_client_info, log_action
from app.services.council_rag import council_rag_answer

router = APIRouter(prefix="/council-chat", tags=["council-chat"])


@router.post("", response_model=CouncilChatResponse)
async def council_chat(
    req: CouncilChatRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Send a chat message with RAG support.

    If session_id is not provided, a new session will be created.
    """
    ip_address, user_agent = get_client_info(request)
    council_uuid = parse_uuid(req.council_id, "審議会ID")

    # Check council access
    check_council_access(db, council_uuid, current_user)

    # Get or create session
    if req.session_id:
        session_uuid = parse_uuid(req.session_id, "セッションID")
        session = (
            db.query(CouncilChatSession)
            .filter(CouncilChatSession.id == session_uuid)
            .first()
        )

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="セッションが見つかりません",
            )

        if session.council_id != council_uuid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="セッションがこの審議会に属していません",
            )
    else:
        # Create new session
        session = CouncilChatSession(
            council_id=council_uuid,
            user_id=current_user.id,
            title=req.question[:50] + "..." if len(req.question) > 50 else req.question,
            selected_meeting_ids=(
                [str(mid) for mid in req.meeting_ids] if req.meeting_ids else None
            ),
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    # Process RAG query
    response = await council_rag_answer(
        db=db,
        req=req,
        user_id=current_user.id,
        session_id=session.id,
    )

    # Add session_id to response
    response.session_id = str(session.id)

    # Log the chat query
    log_action(
        db=db,
        action=AuditAction.COUNCIL_CHAT_QUERY,
        user_id=current_user.id,
        target_type=TargetType.COUNCIL_MESSAGE,
        target_id=response.message_id,
        details={
            "council_id": req.council_id,
            "session_id": str(session.id),
            "use_rag": req.use_rag,
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return response


@router.get("/sessions/{council_id}", response_model=CouncilChatSessionListResponse)
def list_council_chat_sessions(
    council_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List chat sessions for a council.
    """
    council_uuid = parse_uuid(council_id, "審議会ID")
    check_council_access(db, council_uuid, current_user)

    # Get sessions with message counts
    message_count_subq = (
        db.query(
            CouncilMessage.session_id,
            func.count(CouncilMessage.id).label("message_count"),
        )
        .group_by(CouncilMessage.session_id)
        .subquery()
    )

    query = (
        db.query(
            CouncilChatSession.id,
            CouncilChatSession.council_id,
            CouncilChatSession.title,
            CouncilChatSession.selected_meeting_ids,
            CouncilChatSession.created_at,
            CouncilChatSession.updated_at,
            func.coalesce(message_count_subq.c.message_count, 0).label("message_count"),
        )
        .outerjoin(
            message_count_subq, CouncilChatSession.id == message_count_subq.c.session_id
        )
        .filter(
            CouncilChatSession.council_id == council_uuid,
            CouncilChatSession.user_id == current_user.id,
        )
        .order_by(CouncilChatSession.updated_at.desc())
    )

    results = query.all()

    sessions = []
    for row in results:
        sessions.append(
            CouncilChatSessionResponse(
                id=str(row.id),
                council_id=str(row.council_id),
                title=row.title,
                selected_meeting_ids=row.selected_meeting_ids,
                message_count=row.message_count,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
        )

    return CouncilChatSessionListResponse(
        sessions=sessions,
        total=len(sessions),
    )


@router.post(
    "/sessions/{council_id}",
    response_model=CouncilChatSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_council_chat_session(
    council_id: str,
    data: CouncilChatSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new chat session for a council.
    """
    council_uuid = parse_uuid(council_id, "審議会ID")
    check_council_access(db, council_uuid, current_user)

    session = CouncilChatSession(
        council_id=council_uuid,
        user_id=current_user.id,
        title=data.title,
        selected_meeting_ids=(
            [str(mid) for mid in data.selected_meeting_ids]
            if data.selected_meeting_ids
            else None
        ),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return CouncilChatSessionResponse(
        id=str(session.id),
        council_id=str(session.council_id),
        title=session.title,
        selected_meeting_ids=session.selected_meeting_ids,
        message_count=0,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.patch("/sessions/{session_id}", response_model=CouncilChatSessionResponse)
def update_council_chat_session(
    session_id: str,
    data: CouncilChatSessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a chat session (title, selected_meeting_ids).
    """
    session_uuid = parse_uuid(session_id, "セッションID")

    session = (
        db.query(CouncilChatSession)
        .filter(CouncilChatSession.id == session_uuid)
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="セッションが見つかりません",
        )

    # Check council access
    check_council_access(db, session.council_id, current_user)

    # Users can only update their own sessions
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="自分のセッションのみ編集できます",
        )

    if data.title is not None:
        session.title = data.title

    if data.selected_meeting_ids is not None:
        session.selected_meeting_ids = [str(mid) for mid in data.selected_meeting_ids]

    db.commit()
    db.refresh(session)

    # Get message count
    message_count = (
        db.query(func.count(CouncilMessage.id))
        .filter(CouncilMessage.session_id == session.id)
        .scalar()
    )

    return CouncilChatSessionResponse(
        id=str(session.id),
        council_id=str(session.council_id),
        title=session.title,
        selected_meeting_ids=session.selected_meeting_ids,
        message_count=message_count or 0,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_council_chat_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a chat session and all its messages.
    """
    session_uuid = parse_uuid(session_id, "セッションID")

    session = (
        db.query(CouncilChatSession)
        .filter(CouncilChatSession.id == session_uuid)
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="セッションが見つかりません",
        )

    # Check council access
    check_council_access(db, session.council_id, current_user)

    # Users can only delete their own sessions
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="自分のセッションのみ削除できます",
        )

    db.delete(session)
    db.commit()

    return None


@router.get("/history/{session_id}", response_model=CouncilChatHistoryResponse)
def get_council_chat_history(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get chat history for a session.
    """
    session_uuid = parse_uuid(session_id, "セッションID")

    session = (
        db.query(CouncilChatSession)
        .filter(CouncilChatSession.id == session_uuid)
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="セッションが見つかりません",
        )

    # Check council access
    check_council_access(db, session.council_id, current_user)

    # Get messages
    messages = (
        db.query(CouncilMessage)
        .filter(CouncilMessage.session_id == session_uuid)
        .order_by(CouncilMessage.created_at.asc())
        .all()
    )

    message_list = [
        CouncilMessageOut(
            id=str(msg.id),
            session_id=str(msg.session_id),
            role=msg.role,
            content=msg.content,
            source_refs=msg.source_refs,
            created_at=msg.created_at,
        )
        for msg in messages
    ]

    return CouncilChatHistoryResponse(
        session_id=str(session.id),
        council_id=str(session.council_id),
        messages=message_list,
        total=len(message_list),
    )


@router.delete("/history/{council_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_council_chat_history(
    council_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete all chat sessions and messages for a council (user's own sessions only).
    """
    council_uuid = parse_uuid(council_id, "審議会ID")
    check_council_access(db, council_uuid, current_user)

    # Delete only the current user's sessions
    db.query(CouncilChatSession).filter(
        CouncilChatSession.council_id == council_uuid,
        CouncilChatSession.user_id == current_user.id,
    ).delete()
    db.commit()

    return None
