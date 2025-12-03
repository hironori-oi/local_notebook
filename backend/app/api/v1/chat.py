"""
Chat API endpoints with session-based conversation management.

Provides endpoints for:
- Managing chat sessions (create, list, delete)
- Sending messages with conversation history
- Retrieving chat history per session
"""
from typing import List, Optional
from uuid import UUID
import json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.deps import get_db, get_current_user
from app.models.notebook import Notebook
from app.models.chat_session import ChatSession
from app.models.message import Message
from app.models.user import User
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    MessageOut,
    ChatSessionCreate,
    ChatSessionUpdate,
    ChatSessionResponse,
    ChatSessionListResponse,
    ChatHistoryResponse,
)
from app.services.rag import rag_answer
from app.services.audit import log_action, get_client_info, AuditAction, TargetType

router = APIRouter(prefix="/chat", tags=["chat"])


# =============================================================================
# Helper Functions
# =============================================================================

def verify_notebook_ownership(
    db: Session,
    notebook_id: UUID,
    user_id: UUID
) -> Notebook:
    """Verify that the user owns the notebook."""
    notebook = db.query(Notebook).filter(
        Notebook.id == notebook_id,
        Notebook.owner_id == user_id,
    ).first()

    if not notebook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notebookが見つかりません",
        )
    return notebook


def verify_session_ownership(
    db: Session,
    session_id: UUID,
    user_id: UUID
) -> ChatSession:
    """Verify that the user owns the session."""
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == user_id,
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="セッションが見つかりません",
        )
    return session


def parse_uuid(value: str, name: str = "ID") -> UUID:
    """Parse a string to UUID with error handling."""
    try:
        return UUID(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"無効な{name}です",
        )


def message_to_out(msg: Message) -> MessageOut:
    """Convert a Message model to MessageOut schema."""
    source_refs = None
    if msg.source_refs:
        try:
            source_refs = json.loads(msg.source_refs)
        except json.JSONDecodeError:
            source_refs = []

    return MessageOut(
        id=str(msg.id),
        session_id=str(msg.session_id) if msg.session_id else None,
        notebook_id=str(msg.notebook_id),
        user_id=str(msg.user_id) if msg.user_id else None,
        role=msg.role,
        content=msg.content,
        source_refs=source_refs,
        created_at=msg.created_at,
    )


# =============================================================================
# Session Management Endpoints
# =============================================================================

@router.post("/sessions/{notebook_id}", response_model=ChatSessionResponse)
def create_session(
    notebook_id: str,
    data: ChatSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatSessionResponse:
    """
    Create a new chat session for a notebook.
    """
    nb_uuid = parse_uuid(notebook_id, "Notebook ID")
    verify_notebook_ownership(db, nb_uuid, current_user.id)

    session = ChatSession(
        notebook_id=nb_uuid,
        user_id=current_user.id,
        title=data.title,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return ChatSessionResponse(
        id=str(session.id),
        notebook_id=str(session.notebook_id),
        title=session.title,
        message_count=0,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.get("/sessions/{notebook_id}", response_model=ChatSessionListResponse)
def list_sessions(
    notebook_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatSessionListResponse:
    """
    List all chat sessions for a notebook.
    """
    nb_uuid = parse_uuid(notebook_id, "Notebook ID")
    verify_notebook_ownership(db, nb_uuid, current_user.id)

    # Get sessions with message counts
    sessions = db.query(
        ChatSession,
        func.count(Message.id).label("message_count")
    ).outerjoin(
        Message, Message.session_id == ChatSession.id
    ).filter(
        ChatSession.notebook_id == nb_uuid,
        ChatSession.user_id == current_user.id,
    ).group_by(
        ChatSession.id
    ).order_by(
        ChatSession.updated_at.desc()
    ).all()

    session_responses = [
        ChatSessionResponse(
            id=str(session.id),
            notebook_id=str(session.notebook_id),
            title=session.title,
            message_count=message_count,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
        for session, message_count in sessions
    ]

    return ChatSessionListResponse(
        sessions=session_responses,
        total=len(session_responses),
    )


@router.patch("/sessions/{session_id}", response_model=ChatSessionResponse)
def update_session(
    session_id: str,
    data: ChatSessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatSessionResponse:
    """
    Update a chat session (e.g., rename).
    """
    sess_uuid = parse_uuid(session_id, "Session ID")
    session = verify_session_ownership(db, sess_uuid, current_user.id)

    if data.title is not None:
        session.title = data.title

    db.commit()
    db.refresh(session)

    message_count = db.query(func.count(Message.id)).filter(
        Message.session_id == session.id
    ).scalar()

    return ChatSessionResponse(
        id=str(session.id),
        notebook_id=str(session.notebook_id),
        title=session.title,
        message_count=message_count,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a chat session and all its messages.
    """
    sess_uuid = parse_uuid(session_id, "Session ID")
    session = verify_session_ownership(db, sess_uuid, current_user.id)

    db.delete(session)
    db.commit()

    return None


# =============================================================================
# Chat Message Endpoints
# =============================================================================

@router.post("", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    """
    Send a question to the RAG system and get an answer based on notebook sources.

    If session_id is not provided, a new session will be created automatically.
    The conversation history from the session will be included in the LLM context.
    """
    ip_address, user_agent = get_client_info(request)

    nb_uuid = parse_uuid(req.notebook_id, "Notebook ID")
    verify_notebook_ownership(db, nb_uuid, current_user.id)

    # Handle session
    session_id: Optional[UUID] = None
    if req.session_id:
        session_id = parse_uuid(req.session_id, "Session ID")
        session = verify_session_ownership(db, session_id, current_user.id)

        # Verify session belongs to this notebook
        if session.notebook_id != nb_uuid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="セッションはこのノートブックに属していません",
            )
    else:
        # Create new session automatically
        # Generate title from the first question (truncated)
        title = req.question[:50] + "..." if len(req.question) > 50 else req.question
        session = ChatSession(
            notebook_id=nb_uuid,
            user_id=current_user.id,
            title=title,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        session_id = session.id

    # Process with RAG service (now includes session_id)
    res = await rag_answer(
        db=db,
        req=req,
        user_id=current_user.id,
        session_id=session_id,
    )

    # Log chat query
    log_action(
        db=db,
        action=AuditAction.CHAT_QUERY,
        user_id=current_user.id,
        target_type=TargetType.MESSAGE,
        target_id=res.message_id,
        details={
            "notebook_id": req.notebook_id,
            "session_id": str(session_id),
            "question_length": len(req.question),
            "sources_count": len(res.sources),
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )

    # Include session_id in response
    res.session_id = str(session_id)

    return res


@router.get("/history/session/{session_id}", response_model=ChatHistoryResponse)
def get_session_history(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatHistoryResponse:
    """
    Get chat history for a specific session.
    """
    sess_uuid = parse_uuid(session_id, "Session ID")
    session = verify_session_ownership(db, sess_uuid, current_user.id)

    messages = db.query(Message).filter(
        Message.session_id == sess_uuid
    ).order_by(Message.created_at.asc()).all()

    return ChatHistoryResponse(
        session_id=str(session.id),
        messages=[message_to_out(msg) for msg in messages],
        total=len(messages),
    )


@router.get("/history/{notebook_id}", response_model=List[MessageOut])
def get_chat_history(
    notebook_id: str,
    session_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get chat history for a notebook.

    If session_id is provided, returns only messages from that session.
    Otherwise, returns all messages from the notebook (for backward compatibility).
    """
    nb_uuid = parse_uuid(notebook_id, "Notebook ID")
    verify_notebook_ownership(db, nb_uuid, current_user.id)

    query = db.query(Message).filter(Message.notebook_id == nb_uuid)

    if session_id:
        sess_uuid = parse_uuid(session_id, "Session ID")
        query = query.filter(Message.session_id == sess_uuid)

    messages = query.order_by(Message.created_at.asc()).all()

    return [message_to_out(msg) for msg in messages]


@router.delete("/history/{notebook_id}", status_code=status.HTTP_204_NO_CONTENT)
def clear_chat_history(
    notebook_id: str,
    session_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Clear chat history.

    If session_id is provided, clears only that session.
    Otherwise, clears all sessions and messages for the notebook.
    """
    nb_uuid = parse_uuid(notebook_id, "Notebook ID")
    verify_notebook_ownership(db, nb_uuid, current_user.id)

    if session_id:
        sess_uuid = parse_uuid(session_id, "Session ID")
        session = verify_session_ownership(db, sess_uuid, current_user.id)
        db.delete(session)
    else:
        # Delete all sessions (messages will be cascade deleted)
        db.query(ChatSession).filter(
            ChatSession.notebook_id == nb_uuid,
            ChatSession.user_id == current_user.id,
        ).delete()

    db.commit()

    return None
