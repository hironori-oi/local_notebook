"""
Export API endpoints for exporting chat sessions, notebooks, emails, and minutes.
"""

import json
import urllib.parse
from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.chat_session import ChatSession
from app.models.generated_email import GeneratedEmail
from app.models.message import Message
from app.models.minute import Minute
from app.models.notebook import Notebook
from app.models.source import Source
from app.models.user import User
from app.services.export_service import export_service

router = APIRouter(prefix="/export", tags=["export"])


def _encode_filename(filename: str) -> str:
    """Encode filename for Content-Disposition header (RFC 5987)."""
    # Remove any potentially problematic characters
    safe_filename = filename.replace('"', "'").replace("\\", "_")
    # URL encode for filename*
    encoded = urllib.parse.quote(safe_filename, safe="")
    return f"attachment; filename*=UTF-8''{encoded}"


@router.get("/chat/session/{session_id}")
async def export_chat_session(
    session_id: str,
    format: Literal["md", "txt", "json"] = Query("md"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Export a chat session.

    - format: md (Markdown), txt (Plain text), json (JSON)
    """
    # Get session
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")

    # Check ownership via notebook
    notebook = db.query(Notebook).filter(Notebook.id == session.notebook_id).first()
    if not notebook or notebook.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="アクセス権限がありません")

    # Get messages
    messages = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at)
        .all()
    )

    # Format based on requested type
    title = session.title or "chat"
    date_str = datetime.now().strftime("%Y%m%d")

    if format == "json":
        content = export_service.format_chat_json(session, messages, notebook.title)
        filename = f"{title}_{date_str}.json"
        return JSONResponse(
            content=content,
            headers={"Content-Disposition": _encode_filename(filename)},
        )

    if format == "md":
        content = export_service.format_chat_markdown(session, messages, notebook.title)
    else:
        content = export_service.format_chat_text(session, messages, notebook.title)

    filename = f"{title}_{date_str}.{format}"

    return Response(
        content=content.encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": _encode_filename(filename)},
    )


@router.get("/notebook/{notebook_id}")
async def export_notebook(
    notebook_id: str,
    include: str = Query(
        "all",
        description="Comma-separated: all, sources, minutes, chats, emails",
    ),
    format: Literal["md", "txt", "json"] = Query("md"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Export entire notebook content.

    - include: What to include (all, sources, minutes, chats, emails)
    - format: md (Markdown), txt (Plain text), json (JSON)
    """
    # Get notebook
    notebook = db.query(Notebook).filter(Notebook.id == notebook_id).first()
    if not notebook:
        raise HTTPException(status_code=404, detail="ノートブックが見つかりません")

    if notebook.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="アクセス権限がありません")

    # Parse include parameter
    include_items = [item.strip().lower() for item in include.split(",")]
    include_all = "all" in include_items

    # Fetch requested content
    sources = None
    minutes = None
    sessions = None
    emails = None

    if include_all or "sources" in include_items:
        sources = (
            db.query(Source)
            .filter(Source.notebook_id == notebook_id)
            .order_by(Source.created_at.desc())
            .all()
        )

    if include_all or "minutes" in include_items:
        minutes = (
            db.query(Minute)
            .filter(Minute.notebook_id == notebook_id)
            .order_by(Minute.created_at.desc())
            .all()
        )

    if include_all or "chats" in include_items:
        sessions = (
            db.query(ChatSession)
            .filter(ChatSession.notebook_id == notebook_id)
            .order_by(ChatSession.updated_at.desc())
            .all()
        )
        # Load messages for each session
        for session in sessions:
            session.messages = (
                db.query(Message)
                .filter(Message.session_id == session.id)
                .order_by(Message.created_at)
                .all()
            )

    if include_all or "emails" in include_items:
        emails = (
            db.query(GeneratedEmail)
            .filter(GeneratedEmail.notebook_id == notebook_id)
            .order_by(GeneratedEmail.created_at.desc())
            .all()
        )

    # Format content
    title = notebook.title or "notebook"
    date_str = datetime.now().strftime("%Y%m%d")

    if format == "json":
        content = {
            "notebook": {
                "id": str(notebook.id),
                "title": notebook.title,
                "description": notebook.description,
                "created_at": (
                    notebook.created_at.isoformat() if notebook.created_at else None
                ),
            },
            "exported_at": datetime.now().isoformat(),
            "sources": [
                {
                    "id": str(s.id),
                    "title": s.title,
                    "summary": s.summary,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                }
                for s in (sources or [])
            ],
            "minutes": [
                {
                    "id": str(m.id),
                    "title": m.title,
                    "summary": m.summary,
                    "content": m.formatted_content or m.content,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in (minutes or [])
            ],
            "chat_sessions": [
                export_service.format_chat_json(s, s.messages) if s.messages else None
                for s in (sessions or [])
            ],
            "emails": [
                {
                    "id": str(e.id),
                    "title": e.title,
                    "topic": e.topic,
                    "email_body": e.email_body,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in (emails or [])
            ],
        }
        filename = f"{title}_{date_str}.json"
        return JSONResponse(
            content=content,
            headers={"Content-Disposition": _encode_filename(filename)},
        )

    # Markdown format
    content = export_service.format_notebook_markdown(
        notebook, sources, minutes, sessions, emails
    )

    if format == "txt":
        # Simple conversion: just strip markdown syntax
        content = (
            content.replace("#", "").replace("**", "").replace("*", "").replace(">", "")
        )

    filename = f"{title}_{date_str}.{format}"

    return Response(
        content=content.encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": _encode_filename(filename)},
    )


@router.get("/email/{email_id}")
async def export_email(
    email_id: str,
    format: Literal["md", "txt"] = Query("txt"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Export a generated email.

    - format: md (Markdown), txt (Plain text)
    """
    # Get email
    email = db.query(GeneratedEmail).filter(GeneratedEmail.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="メールが見つかりません")

    # Check ownership via notebook
    notebook = db.query(Notebook).filter(Notebook.id == email.notebook_id).first()
    if not notebook or notebook.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="アクセス権限がありません")

    # Format content
    title = email.title or "email"
    date_str = datetime.now().strftime("%Y%m%d")

    if format == "md":
        content = export_service.format_email_markdown(email, notebook.title)
    else:
        content = export_service.format_email_text(email, notebook.title)

    filename = f"{title}_{date_str}.{format}"

    return Response(
        content=content.encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": _encode_filename(filename)},
    )


@router.get("/minute/{minute_id}")
async def export_minute(
    minute_id: str,
    format: Literal["md", "txt"] = Query("md"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Export a minute.

    - format: md (Markdown), txt (Plain text)
    """
    # Get minute
    minute = db.query(Minute).filter(Minute.id == minute_id).first()
    if not minute:
        raise HTTPException(status_code=404, detail="議事録が見つかりません")

    # Check ownership via notebook
    notebook = db.query(Notebook).filter(Notebook.id == minute.notebook_id).first()
    if not notebook or notebook.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="アクセス権限がありません")

    # Format content
    title = minute.title or "minute"
    date_str = datetime.now().strftime("%Y%m%d")

    if format == "md":
        content = export_service.format_minute_markdown(minute, notebook.title)
    else:
        content = export_service.format_minute_text(minute, notebook.title)

    filename = f"{title}_{date_str}.{format}"

    return Response(
        content=content.encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": _encode_filename(filename)},
    )
