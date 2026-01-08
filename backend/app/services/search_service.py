"""
Search service for global search across notebooks, sources, minutes, and messages.
"""

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass
class SearchResult:
    """Search result item."""
    type: Literal["notebook", "source", "minute", "message"]
    id: str
    title: str
    snippet: str
    notebook_id: str | None
    notebook_title: str | None
    relevance_score: float
    created_at: datetime | None


class SearchService:
    """Service for performing global search across all content types."""

    def __init__(self, db: Session, user_id: UUID):
        self.db = db
        self.user_id = user_id

    async def search_all(
        self,
        query: str,
        types: list[str],
        limit: int,
        offset: int,
    ) -> tuple[list[SearchResult], int, float]:
        """
        Perform search across all requested types.

        Returns:
            Tuple of (results, total_count, search_time_ms)
        """
        start_time = time.time()
        results: list[SearchResult] = []

        include_all = "all" in types

        if include_all or "notebook" in types:
            results.extend(self._search_notebooks(query))
        if include_all or "source" in types:
            results.extend(self._search_sources(query))
        if include_all or "minute" in types:
            results.extend(self._search_minutes(query))
        if include_all or "message" in types:
            results.extend(self._search_messages(query))

        # Sort by relevance score
        results.sort(key=lambda x: x.relevance_score, reverse=True)

        total = len(results)
        paginated = results[offset:offset + limit]

        search_time_ms = (time.time() - start_time) * 1000

        return paginated, total, search_time_ms

    def _search_notebooks(self, query: str) -> list[SearchResult]:
        """Search notebooks by title and description."""
        pattern = f"%{query}%"

        sql = text("""
            SELECT
                id,
                title,
                description,
                created_at,
                CASE
                    WHEN title ILIKE :pattern THEN 2.0
                    WHEN description ILIKE :pattern THEN 1.0
                    ELSE 0.5
                END as relevance
            FROM notebooks
            WHERE owner_id = :user_id
              AND (title ILIKE :pattern OR description ILIKE :pattern)
            ORDER BY relevance DESC, updated_at DESC
            LIMIT 20
        """)

        result = self.db.execute(
            sql,
            {"user_id": self.user_id, "pattern": pattern}
        )

        items = []
        for row in result:
            # Create snippet from title or description
            snippet = row.description[:100] + "..." if row.description and len(row.description) > 100 else (row.description or "")

            items.append(SearchResult(
                type="notebook",
                id=str(row.id),
                title=row.title,
                snippet=snippet,
                notebook_id=None,
                notebook_title=None,
                relevance_score=float(row.relevance),
                created_at=row.created_at,
            ))

        return items

    def _search_sources(self, query: str) -> list[SearchResult]:
        """Search sources by title and summary."""
        pattern = f"%{query}%"

        sql = text("""
            SELECT
                s.id,
                s.title,
                s.summary,
                s.notebook_id,
                n.title as notebook_title,
                s.created_at,
                CASE
                    WHEN s.title ILIKE :pattern THEN 2.0
                    WHEN s.summary ILIKE :pattern THEN 1.5
                    ELSE 0.5
                END as relevance
            FROM sources s
            JOIN notebooks n ON s.notebook_id = n.id
            WHERE n.owner_id = :user_id
              AND (s.title ILIKE :pattern OR s.summary ILIKE :pattern)
            ORDER BY relevance DESC, s.created_at DESC
            LIMIT 20
        """)

        result = self.db.execute(
            sql,
            {"user_id": self.user_id, "pattern": pattern}
        )

        items = []
        for row in result:
            snippet = row.summary[:100] + "..." if row.summary and len(row.summary) > 100 else (row.summary or "")

            items.append(SearchResult(
                type="source",
                id=str(row.id),
                title=row.title,
                snippet=snippet,
                notebook_id=str(row.notebook_id),
                notebook_title=row.notebook_title,
                relevance_score=float(row.relevance),
                created_at=row.created_at,
            ))

        return items

    def _search_minutes(self, query: str) -> list[SearchResult]:
        """Search minutes by title, content, and summary."""
        pattern = f"%{query}%"

        sql = text("""
            SELECT
                m.id,
                m.title,
                m.content,
                m.summary,
                m.notebook_id,
                n.title as notebook_title,
                m.created_at,
                CASE
                    WHEN m.title ILIKE :pattern THEN 2.0
                    WHEN m.summary ILIKE :pattern THEN 1.5
                    WHEN m.content ILIKE :pattern THEN 1.0
                    ELSE 0.5
                END as relevance
            FROM minutes m
            JOIN notebooks n ON m.notebook_id = n.id
            WHERE n.owner_id = :user_id
              AND (m.title ILIKE :pattern OR m.content ILIKE :pattern OR m.summary ILIKE :pattern)
            ORDER BY relevance DESC, m.created_at DESC
            LIMIT 20
        """)

        result = self.db.execute(
            sql,
            {"user_id": self.user_id, "pattern": pattern}
        )

        items = []
        for row in result:
            # Prefer summary for snippet, fallback to content
            text_source = row.summary or row.content or ""
            snippet = text_source[:100] + "..." if len(text_source) > 100 else text_source

            items.append(SearchResult(
                type="minute",
                id=str(row.id),
                title=row.title,
                snippet=snippet,
                notebook_id=str(row.notebook_id),
                notebook_title=row.notebook_title,
                relevance_score=float(row.relevance),
                created_at=row.created_at,
            ))

        return items

    def _search_messages(self, query: str) -> list[SearchResult]:
        """Search messages by content."""
        pattern = f"%{query}%"

        sql = text("""
            SELECT
                m.id,
                m.content,
                m.role,
                m.notebook_id,
                n.title as notebook_title,
                cs.id as session_id,
                cs.title as session_title,
                m.created_at,
                1.0 as relevance
            FROM messages m
            JOIN notebooks n ON m.notebook_id = n.id
            LEFT JOIN chat_sessions cs ON m.session_id = cs.id
            WHERE n.owner_id = :user_id
              AND m.content ILIKE :pattern
            ORDER BY m.created_at DESC
            LIMIT 20
        """)

        result = self.db.execute(
            sql,
            {"user_id": self.user_id, "pattern": pattern}
        )

        items = []
        for row in result:
            # Use part of content as snippet
            content = row.content or ""
            snippet = content[:120] + "..." if len(content) > 120 else content

            # Title shows role and session info
            role_label = "ユーザー" if row.role == "user" else "アシスタント"
            session_name = row.session_title or "チャット"
            title = f"[{role_label}] {session_name}"

            items.append(SearchResult(
                type="message",
                id=str(row.id),
                title=title,
                snippet=snippet,
                notebook_id=str(row.notebook_id),
                notebook_title=row.notebook_title,
                relevance_score=float(row.relevance),
                created_at=row.created_at,
            ))

        return items

    def get_recent_items(self, limit: int = 10) -> list[SearchResult]:
        """Get recently accessed/created items across all types."""
        results: list[SearchResult] = []

        # Recent notebooks
        sql = text("""
            SELECT id, title, description, created_at, updated_at
            FROM notebooks
            WHERE owner_id = :user_id
            ORDER BY updated_at DESC
            LIMIT :limit
        """)
        for row in self.db.execute(sql, {"user_id": self.user_id, "limit": limit // 2}):
            results.append(SearchResult(
                type="notebook",
                id=str(row.id),
                title=row.title,
                snippet=row.description[:80] + "..." if row.description and len(row.description) > 80 else (row.description or ""),
                notebook_id=None,
                notebook_title=None,
                relevance_score=1.0,
                created_at=row.updated_at or row.created_at,
            ))

        # Recent sources
        sql = text("""
            SELECT s.id, s.title, s.summary, s.notebook_id, n.title as notebook_title, s.created_at
            FROM sources s
            JOIN notebooks n ON s.notebook_id = n.id
            WHERE n.owner_id = :user_id
            ORDER BY s.created_at DESC
            LIMIT :limit
        """)
        for row in self.db.execute(sql, {"user_id": self.user_id, "limit": limit // 2}):
            results.append(SearchResult(
                type="source",
                id=str(row.id),
                title=row.title,
                snippet=row.summary[:80] + "..." if row.summary and len(row.summary) > 80 else (row.summary or ""),
                notebook_id=str(row.notebook_id),
                notebook_title=row.notebook_title,
                relevance_score=1.0,
                created_at=row.created_at,
            ))

        # Sort by created_at and limit
        results.sort(key=lambda x: x.created_at or datetime.min, reverse=True)
        return results[:limit]
