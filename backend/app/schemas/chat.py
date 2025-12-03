"""
Chat schemas for request/response validation.

Includes session management schemas for maintaining conversation context.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# =============================================================================
# Chat Session Schemas
# =============================================================================

class ChatSessionCreate(BaseModel):
    """Request schema for creating a new chat session."""
    title: Optional[str] = Field(
        None,
        max_length=255,
        description="Optional title for the session. Auto-generated from first message if not provided."
    )


class ChatSessionUpdate(BaseModel):
    """Request schema for updating a chat session."""
    title: Optional[str] = Field(None, max_length=255)


class ChatSessionResponse(BaseModel):
    """Response schema for a chat session."""
    id: str
    notebook_id: str
    title: Optional[str] = None
    message_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatSessionListResponse(BaseModel):
    """Response schema for listing chat sessions."""
    sessions: List[ChatSessionResponse]
    total: int


# =============================================================================
# Chat Message Schemas
# =============================================================================

class ChatRequest(BaseModel):
    """Request schema for sending a chat message."""
    notebook_id: str
    session_id: Optional[str] = Field(
        None,
        description="Session ID. If not provided, a new session will be created."
    )
    source_ids: List[str] = Field(
        default_factory=list,
        description="Source IDs to search. Empty means all sources in notebook."
    )
    question: str = Field(..., min_length=1, max_length=10000)
    use_rag: bool = Field(
        True,
        description="Whether to use RAG search. If False, direct LLM conversation."
    )


class ChatResponse(BaseModel):
    """Response schema for a chat message."""
    answer: str
    sources: List[str]  # "資料名(p.xx)" のような表示用文字列
    message_id: Optional[str] = None  # 保存されたメッセージのID
    session_id: Optional[str] = None  # セッションID


class MessageOut(BaseModel):
    """Response schema for a single message."""
    id: str
    session_id: Optional[str] = None
    notebook_id: str
    user_id: Optional[str] = None
    role: str
    content: str
    source_refs: Optional[List[str]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatHistoryResponse(BaseModel):
    """Response schema for chat history."""
    session_id: str
    messages: List[MessageOut]
    total: int
