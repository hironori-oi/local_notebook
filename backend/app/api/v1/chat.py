"""
Chat API endpoints with session-based conversation management.

Provides endpoints for:
- Managing chat sessions (create, list, delete)
- Sending messages with conversation history
- Retrieving chat history per session
"""

import json
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.celery_app.tasks.chat import enqueue_chat_processing
from app.core.config import settings
from app.core.deps import check_notebook_access, get_current_user, get_db, parse_uuid
from app.models.chat_session import ChatSession
from app.models.message import Message
from app.models.notebook import Notebook
from app.models.user import User
from app.schemas.chat import (
    AsyncChatResponse,
    ChatHistoryResponse,
    ChatRequest,
    ChatResponse,
    ChatSessionCreate,
    ChatSessionListResponse,
    ChatSessionResponse,
    ChatSessionUpdate,
    MessageOut,
    MessageStatusResponse,
)
from app.services.audit import AuditAction, TargetType, get_client_info, log_action
from app.services.rag import rag_answer, rag_answer_stream

router = APIRouter(prefix="/chat", tags=["chat"])


# =============================================================================
# Helper Functions
# =============================================================================


def verify_notebook_access(db: Session, notebook_id: UUID, user: User) -> Notebook:
    """Verify that the user can access the notebook (owner or public)."""
    return check_notebook_access(db, notebook_id, user)


def verify_session_ownership(
    db: Session, session_id: UUID, user_id: UUID
) -> ChatSession:
    """Verify that the user owns the session."""
    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id,
        )
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="セッションが見つかりません",
        )
    return session


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
        status=getattr(msg, "status", "completed"),
        error_message=getattr(msg, "error_message", None),
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
    verify_notebook_access(db, nb_uuid, current_user)

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
    verify_notebook_access(db, nb_uuid, current_user)

    # Get sessions with message counts
    sessions = (
        db.query(ChatSession, func.count(Message.id).label("message_count"))
        .outerjoin(Message, Message.session_id == ChatSession.id)
        .filter(
            ChatSession.notebook_id == nb_uuid,
            ChatSession.user_id == current_user.id,
        )
        .group_by(ChatSession.id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )

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

    message_count = (
        db.query(func.count(Message.id))
        .filter(Message.session_id == session.id)
        .scalar()
    )

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
    verify_notebook_access(db, nb_uuid, current_user)

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


@router.post("/stream")
async def chat_stream(
    req: ChatRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """
    Send a question and receive a streaming response via Server-Sent Events (SSE).

    This endpoint provides real-time streaming of the LLM response for better UX.
    The response is formatted as SSE with the following event types:
    - data: <content> - Partial response content
    - data: [SOURCES]<json_array> - Source references when complete
    - data: [DONE] - Completion signal
    - data: [ERROR]<message> - Error message if something fails

    If session_id is not provided, a new session will be created automatically.
    """
    nb_uuid = parse_uuid(req.notebook_id, "Notebook ID")
    verify_notebook_access(db, nb_uuid, current_user)

    # Handle session
    session_id: Optional[UUID] = None
    if req.session_id:
        session_id = parse_uuid(req.session_id, "Session ID")
        session = verify_session_ownership(db, session_id, current_user.id)

        if session.notebook_id != nb_uuid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="セッションはこのノートブックに属していません",
            )
    else:
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

    async def stream_generator():
        """Generate SSE stream from RAG service."""
        # First yield the session_id for client reference
        yield f"data: [SESSION]{str(session_id)}\n\n"

        async for chunk in rag_answer_stream(
            db=db,
            req=req,
            user_id=current_user.id,
            session_id=session_id,
        ):
            yield chunk

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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

    messages = (
        db.query(Message)
        .filter(Message.session_id == sess_uuid)
        .order_by(Message.created_at.asc())
        .all()
    )

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
    verify_notebook_access(db, nb_uuid, current_user)

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
    verify_notebook_access(db, nb_uuid, current_user)

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


# =============================================================================
# Async Chat Endpoints
# =============================================================================


@router.post("/async", response_model=AsyncChatResponse)
async def chat_async(
    req: ChatRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AsyncChatResponse:
    """
    Submit a chat question for background processing.

    This endpoint returns immediately with message IDs, and the actual
    LLM generation happens in a background task. Use the /chat/status/{message_id}
    endpoint to check the generation status and retrieve the result.

    This allows the chat to continue even if the user navigates away or
    closes the browser.
    """
    ip_address, user_agent = get_client_info(request)

    nb_uuid = parse_uuid(req.notebook_id, "Notebook ID")
    verify_notebook_access(db, nb_uuid, current_user)

    # Handle session
    session_id: Optional[UUID] = None
    if req.session_id:
        session_id = parse_uuid(req.session_id, "Session ID")
        session = verify_session_ownership(db, session_id, current_user.id)

        if session.notebook_id != nb_uuid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="セッションはこのノートブックに属していません",
            )
    else:
        # Create new session automatically
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

    # Create user message (completed status)
    user_message = Message(
        notebook_id=nb_uuid,
        session_id=session_id,
        user_id=current_user.id,
        role="user",
        content=req.question,
        status="completed",
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    # Create assistant message with pending status
    assistant_message = Message(
        notebook_id=nb_uuid,
        session_id=session_id,
        user_id=None,
        role="assistant",
        content="",  # Will be filled by background processor
        status="pending",
    )
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)

    # Schedule Celery task for chat processing
    enqueue_chat_processing(
        message_id=assistant_message.id,
        notebook_id=nb_uuid,
        session_id=session_id,
        question=req.question,
        source_ids=req.source_ids if req.source_ids else None,
        use_rag=req.use_rag,
        use_formatted_text=req.use_formatted_text,
    )

    # Log chat query
    log_action(
        db=db,
        action=AuditAction.CHAT_QUERY,
        user_id=current_user.id,
        target_type=TargetType.MESSAGE,
        target_id=str(assistant_message.id),
        details={
            "notebook_id": req.notebook_id,
            "session_id": str(session_id),
            "question_length": len(req.question),
            "async": True,
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return AsyncChatResponse(
        user_message_id=str(user_message.id),
        assistant_message_id=str(assistant_message.id),
        session_id=str(session_id),
        status="pending",
    )


@router.get("/status/{message_id}", response_model=MessageStatusResponse)
def get_message_status(
    message_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageStatusResponse:
    """
    Check the status of a message being generated.

    Returns the current status and content if completed.
    """
    msg_uuid = parse_uuid(message_id, "Message ID")

    # Find the message
    message = db.query(Message).filter(Message.id == msg_uuid).first()

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="メッセージが見つかりません",
        )

    # Verify user access through session or notebook
    if message.session_id:
        session = (
            db.query(ChatSession).filter(ChatSession.id == message.session_id).first()
        )
        if session and session.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="このメッセージにアクセスする権限がありません",
            )
    else:
        # Check notebook access
        verify_notebook_access(db, message.notebook_id, current_user)

    # Parse source_refs
    source_refs = None
    if message.source_refs:
        try:
            source_refs = json.loads(message.source_refs)
        except json.JSONDecodeError:
            source_refs = []

    return MessageStatusResponse(
        message_id=str(message.id),
        status=getattr(message, "status", "completed"),
        content=message.content if message.content else None,
        source_refs=source_refs,
        error_message=getattr(message, "error_message", None),
    )
