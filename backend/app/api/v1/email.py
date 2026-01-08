"""
Email API endpoints for generating and managing email content.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.deps import check_notebook_access, get_current_user, get_db, parse_uuid
from app.models.generated_email import GeneratedEmail
from app.models.notebook import Notebook
from app.models.user import User
from app.schemas.email import (
    EmailGenerateRequest,
    EmailGenerateResponse,
    GeneratedEmailCreate,
    GeneratedEmailOut,
    GeneratedEmailUpdate,
)
from app.services.audit import AuditAction, TargetType, get_client_info, log_action
from app.services.email_generator import generate_email_content

router = APIRouter(prefix="/emails", tags=["emails"])


def _verify_notebook_access(db: Session, notebook_id: UUID, user: User) -> Notebook:
    """Verify that the user can access the notebook (owner or public)."""
    return check_notebook_access(db, notebook_id, user)


@router.post("/generate/{notebook_id}", response_model=EmailGenerateResponse)
async def generate_email(
    notebook_id: str,
    data: EmailGenerateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate email content from notebook sources.

    Uses RAG to retrieve relevant context from documents and meeting minutes,
    then uses LLM to generate a structured email body.
    """
    ip_address, user_agent = get_client_info(request)
    nb_uuid = parse_uuid(notebook_id, "Notebook ID")
    _verify_notebook_access(db, nb_uuid, current_user)

    # Generate email content using LLM
    result = await generate_email_content(
        db=db,
        notebook_id=nb_uuid,
        topic=data.topic,
        document_source_ids=data.document_source_ids,
        minute_ids=data.minute_ids,
        user_id=current_user.id,
    )

    # Log action
    log_action(
        db=db,
        action=AuditAction.GENERATE_EMAIL,
        user_id=current_user.id,
        target_type=TargetType.EMAIL,
        target_id=str(nb_uuid),
        details={
            "topic": data.topic,
            "document_sources": len(data.document_source_ids),
            "minutes": len(data.minute_ids),
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return result


@router.post(
    "/{notebook_id}",
    response_model=GeneratedEmailOut,
    status_code=status.HTTP_201_CREATED,
)
def save_email(
    notebook_id: str,
    data: GeneratedEmailCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Save a generated email to the database.

    Use this endpoint after generating and optionally editing email content.
    """
    ip_address, user_agent = get_client_info(request)
    nb_uuid = parse_uuid(notebook_id, "Notebook ID")
    _verify_notebook_access(db, nb_uuid, current_user)

    # Create email record
    email = GeneratedEmail(
        notebook_id=nb_uuid,
        created_by=current_user.id,
        title=data.title,
        topic=data.topic,
        email_body=data.email_body,
        structured_content=(
            data.structured_content.model_dump() if data.structured_content else None
        ),
        document_source_ids=(
            data.document_source_ids if data.document_source_ids else None
        ),
        minute_ids=data.minute_ids if data.minute_ids else None,
    )
    db.add(email)
    db.commit()
    db.refresh(email)

    # Log action
    log_action(
        db=db,
        action=AuditAction.SAVE_EMAIL,
        user_id=current_user.id,
        target_type=TargetType.EMAIL,
        target_id=str(email.id),
        details={"title": email.title, "topic": email.topic},
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return email


@router.get("/{notebook_id}", response_model=List[GeneratedEmailOut])
def list_emails(
    notebook_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all saved emails for a notebook.
    """
    nb_uuid = parse_uuid(notebook_id, "Notebook ID")
    _verify_notebook_access(db, nb_uuid, current_user)

    emails = (
        db.query(GeneratedEmail)
        .filter(
            GeneratedEmail.notebook_id == nb_uuid,
            GeneratedEmail.created_by == current_user.id,
        )
        .order_by(GeneratedEmail.created_at.desc())
        .all()
    )

    return emails


@router.get("/detail/{email_id}", response_model=GeneratedEmailOut)
def get_email(
    email_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific saved email by ID.
    """
    email_uuid = parse_uuid(email_id, "Email ID")

    email = (
        db.query(GeneratedEmail)
        .filter(
            GeneratedEmail.id == email_uuid,
            GeneratedEmail.created_by == current_user.id,
        )
        .first()
    )

    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="メールが見つかりません",
        )

    return email


@router.patch("/{email_id}", response_model=GeneratedEmailOut)
def update_email(
    email_id: str,
    data: GeneratedEmailUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a saved email's title or body.
    """
    email_uuid = parse_uuid(email_id, "Email ID")

    email = (
        db.query(GeneratedEmail)
        .filter(
            GeneratedEmail.id == email_uuid,
            GeneratedEmail.created_by == current_user.id,
        )
        .first()
    )

    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="メールが見つかりません",
        )

    if data.title is not None:
        email.title = data.title
    if data.email_body is not None:
        email.email_body = data.email_body

    db.commit()
    db.refresh(email)

    return email


@router.delete("/{email_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_email(
    email_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a saved email.
    """
    ip_address, user_agent = get_client_info(request)
    email_uuid = parse_uuid(email_id, "Email ID")

    email = (
        db.query(GeneratedEmail)
        .filter(
            GeneratedEmail.id == email_uuid,
            GeneratedEmail.created_by == current_user.id,
        )
        .first()
    )

    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="メールが見つかりません",
        )

    title = email.title

    db.delete(email)
    db.commit()

    # Log action
    log_action(
        db=db,
        action=AuditAction.DELETE_EMAIL,
        user_id=current_user.id,
        target_type=TargetType.EMAIL,
        target_id=email_id,
        details={"title": title},
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return None
