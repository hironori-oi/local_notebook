"""
Audit logging service.

This module provides functions to log user actions for compliance and security monitoring.
"""
import logging
from typing import Optional
from uuid import UUID
import json

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


class AuditAction:
    """Constants for audit actions."""

    # Authentication
    LOGIN = "login"
    LOGOUT = "logout"
    REGISTER = "register"
    LOGIN_FAILED = "login_failed"

    # Notebooks
    CREATE_NOTEBOOK = "create_notebook"
    DELETE_NOTEBOOK = "delete_notebook"
    VIEW_NOTEBOOK = "view_notebook"

    # Sources
    UPLOAD_SOURCE = "upload_source"
    DELETE_SOURCE = "delete_source"

    # Chat
    CHAT_QUERY = "chat_query"

    # Notes
    CREATE_NOTE = "create_note"
    DELETE_NOTE = "delete_note"

    # Infographics
    CREATE_INFOGRAPHIC = "create_infographic"
    DELETE_INFOGRAPHIC = "delete_infographic"

    # Slide Decks
    CREATE_SLIDE_DECK = "create_slide_deck"
    DELETE_SLIDE_DECK = "delete_slide_deck"
    DOWNLOAD_SLIDE_DECK = "download_slide_deck"


class TargetType:
    """Constants for audit target types."""

    USER = "user"
    NOTEBOOK = "notebook"
    SOURCE = "source"
    MESSAGE = "message"
    NOTE = "note"
    INFOGRAPHIC = "infographic"
    SLIDE_DECK = "slide_deck"


def get_client_info(request: Request) -> tuple[Optional[str], Optional[str]]:
    """
    Extract client IP and user agent from request.

    Args:
        request: FastAPI request object

    Returns:
        Tuple of (ip_address, user_agent)
    """
    # Get IP address
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip_address = forwarded.split(",")[0].strip()
    else:
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            ip_address = real_ip.strip()
        elif request.client:
            ip_address = request.client.host
        else:
            ip_address = None

    # Get user agent
    user_agent = request.headers.get("User-Agent")

    return ip_address, user_agent


def log_action(
    db: Session,
    action: str,
    user_id: Optional[UUID] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> AuditLog:
    """
    Log an audit event.

    Args:
        db: Database session
        action: Action type (use AuditAction constants)
        user_id: User who performed the action
        target_type: Type of resource affected (e.g., "notebook", "source")
        target_id: ID of the affected resource
        details: Additional details as a dictionary
        ip_address: Client IP address
        user_agent: Client user agent string

    Returns:
        Created AuditLog record
    """
    log = AuditLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=json.dumps(details) if details else None,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def log_action_async(
    db: Session,
    action: str,
    user_id: Optional[UUID] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """
    Log an audit event without blocking (fire and forget).

    Note: In a production environment, this should use a background
    task queue (e.g., Celery, RQ) for true async logging.
    """
    try:
        log_action(
            db=db,
            action=action,
            user_id=user_id,
            target_type=target_type,
            target_id=target_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except Exception:
        # Don't fail the request if logging fails
        pass
