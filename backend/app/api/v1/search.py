"""
Search API endpoints for global search functionality.
"""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["search"])


class SearchResultItem(BaseModel):
    """Search result item schema."""

    type: Literal["notebook", "source", "minute", "message"]
    id: str
    title: str
    snippet: str
    notebook_id: str | None
    notebook_title: str | None
    relevance_score: float
    created_at: datetime | None

    class Config:
        from_attributes = True


class SearchResponse(BaseModel):
    """Search response with results and metadata."""

    query: str
    results: list[SearchResultItem]
    total: int
    search_time_ms: float


@router.get("/global", response_model=SearchResponse)
async def global_search(
    q: str = Query(..., min_length=1, max_length=200, description="検索クエリ"),
    types: str = Query(
        "all",
        description="検索対象タイプ（カンマ区切り: all, notebook, source, minute, message）",
    ),
    limit: int = Query(20, ge=1, le=100, description="取得件数"),
    offset: int = Query(0, ge=0, description="オフセット"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SearchResponse:
    """
    グローバル検索エンドポイント

    ノートブック、資料、議事録、チャットメッセージを横断して検索します。
    ユーザーが所有するコンテンツのみが検索対象となります。

    - **q**: 検索クエリ（1-200文字）
    - **types**: 検索対象タイプ（all, notebook, source, minute, message のカンマ区切り）
    - **limit**: 取得件数（1-100）
    - **offset**: ページネーション用オフセット
    """
    # Parse types
    type_list = [t.strip().lower() for t in types.split(",")]

    # Perform search
    search_service = SearchService(db, current_user.id)
    results, total, search_time_ms = await search_service.search_all(
        query=q,
        types=type_list,
        limit=limit,
        offset=offset,
    )

    # Convert to response items
    result_items = [
        SearchResultItem(
            type=r.type,
            id=r.id,
            title=r.title,
            snippet=r.snippet,
            notebook_id=r.notebook_id,
            notebook_title=r.notebook_title,
            relevance_score=r.relevance_score,
            created_at=r.created_at,
        )
        for r in results
    ]

    return SearchResponse(
        query=q,
        results=result_items,
        total=total,
        search_time_ms=search_time_ms,
    )


@router.get("/recent", response_model=list[SearchResultItem])
async def get_recent_items(
    limit: int = Query(10, ge=1, le=50, description="取得件数"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SearchResultItem]:
    """
    最近のアイテム一覧を取得

    検索モーダルを開いた際に、最近アクセス/作成したアイテムを表示します。
    """
    search_service = SearchService(db, current_user.id)
    results = search_service.get_recent_items(limit=limit)

    return [
        SearchResultItem(
            type=r.type,
            id=r.id,
            title=r.title,
            snippet=r.snippet,
            notebook_id=r.notebook_id,
            notebook_title=r.notebook_title,
            relevance_score=r.relevance_score,
            created_at=r.created_at,
        )
        for r in results
    ]
