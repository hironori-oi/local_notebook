"""Schemas for council chat operations."""
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime


# =============================================================================
# Council Chat Session Schemas
# =============================================================================

class CouncilChatSessionCreate(BaseModel):
    """Request schema for creating a council chat session."""
    title: Optional[str] = Field(
        None,
        max_length=255,
        description="セッションタイトル（省略時は最初の質問から自動生成）"
    )
    selected_meeting_ids: Optional[List[UUID]] = Field(
        None,
        description="RAGコンテキストに使用する開催回ID一覧"
    )


class CouncilChatSessionUpdate(BaseModel):
    """Request schema for updating a council chat session."""
    title: Optional[str] = Field(None, max_length=255)
    selected_meeting_ids: Optional[List[UUID]] = Field(
        None,
        description="RAGコンテキストに使用する開催回ID一覧"
    )


class CouncilChatSessionResponse(BaseModel):
    """Response schema for a council chat session."""
    id: str
    council_id: str
    title: Optional[str] = None
    selected_meeting_ids: Optional[List[str]] = None
    message_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CouncilChatSessionListResponse(BaseModel):
    """Response schema for listing council chat sessions."""
    sessions: List[CouncilChatSessionResponse]
    total: int


# =============================================================================
# Council Chat Message Schemas
# =============================================================================

class CouncilChatRequest(BaseModel):
    """Request schema for sending a council chat message."""
    council_id: str = Field(..., description="審議会ID")
    session_id: Optional[str] = Field(
        None,
        description="セッションID（省略時は新規セッション作成）"
    )
    meeting_ids: List[str] = Field(
        default_factory=list,
        description="検索対象の開催回ID一覧（空の場合は全開催回）"
    )
    agenda_ids: List[str] = Field(
        default_factory=list,
        description="検索対象の議題ID一覧（空の場合は選択された開催回の全議題）"
    )
    question: str = Field(..., min_length=1, max_length=10000)
    use_rag: bool = Field(
        True,
        description="RAG検索を使用するか（Falseの場合は直接LLM会話）"
    )


class CouncilChatResponse(BaseModel):
    """Response schema for a council chat message."""
    answer: str
    sources: List[dict] = Field(
        description="参照元情報 [{meeting_id, meeting_number, type, excerpt}]"
    )
    message_id: Optional[str] = None
    session_id: Optional[str] = None


class CouncilMessageOut(BaseModel):
    """Response schema for a single council message."""
    id: str
    session_id: str
    role: str
    content: str
    source_refs: Optional[List[dict]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CouncilChatHistoryResponse(BaseModel):
    """Response schema for council chat history."""
    session_id: str
    council_id: str
    messages: List[CouncilMessageOut]
    total: int
