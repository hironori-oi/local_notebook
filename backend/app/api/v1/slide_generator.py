"""
Slide Generator API - Generate PowerPoint presentations from text.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional
from uuid import UUID

from fastapi import (APIRouter, BackgroundTasks, Depends, File, Form,
                     HTTPException, Query, UploadFile, status)
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.celery_app.tasks.slide import enqueue_slide_generation
from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.models.slide_project import (SlideContent, SlideMessage, SlideProject,
                                      SlideStyle, SlideTemplate)
from app.models.user import User
from app.schemas.slide_generator import (MessageOut, ProjectCreate,
                                         ProjectDetail, ProjectListResponse,
                                         ProjectSummary, RefineRequest,
                                         RefineResponse, SlideOut, SlideUpdate,
                                         StyleCreate, StyleListResponse,
                                         StyleOut, StyleUpdate,
                                         TemplateListResponse, TemplateOut)
from app.services.pptx_extractor import get_slide_count
from app.services.slide_builder import build_pptx_from_project
from app.services.slide_generator import generate_slides, refine_slides

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/slide-generator", tags=["slide-generator"])


# =============================================================================
# Project endpoints
# =============================================================================


@router.post(
    "/projects", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED
)
async def create_project(
    request: ProjectCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new slide generation project and start generation."""
    # Create project
    project = SlideProject(
        user_id=current_user.id,
        title=request.title,
        source_text=request.source_text,
        target_slide_count=request.target_slide_count,
        key_points=request.key_points,
        template_id=request.template_id,
        style_id=request.style_id,
        status="pending",
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    # Schedule Celery task for slide generation
    enqueue_slide_generation(project.id)

    logger.info(f"Created slide project: {project.id}")

    return ProjectDetail(
        id=project.id,
        title=project.title,
        source_text=project.source_text,
        target_slide_count=project.target_slide_count,
        key_points=project.key_points,
        template_id=project.template_id,
        style_id=project.style_id,
        status=project.status,
        error_message=project.error_message,
        slides=[],
        messages=[],
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.get("/projects", response_model=ProjectListResponse)
async def list_projects(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List user's slide projects."""
    from sqlalchemy import func

    query = db.query(SlideProject).filter(SlideProject.user_id == current_user.id)
    total = query.count()

    projects = (
        query.order_by(SlideProject.created_at.desc()).offset(offset).limit(limit).all()
    )

    if not projects:
        return ProjectListResponse(items=[], total=total, offset=offset, limit=limit)

    # Batch fetch slide counts to avoid N+1 queries
    project_ids = [p.id for p in projects]
    slide_counts = (
        db.query(SlideContent.project_id, func.count(SlideContent.id).label("count"))
        .filter(SlideContent.project_id.in_(project_ids))
        .group_by(SlideContent.project_id)
        .all()
    )

    count_map = {row.project_id: row.count for row in slide_counts}

    items = []
    for project in projects:
        items.append(
            ProjectSummary(
                id=project.id,
                title=project.title,
                status=project.status,
                slide_count=count_map.get(project.id, 0),
                created_at=project.created_at,
                updated_at=project.updated_at,
            )
        )

    return ProjectListResponse(
        items=items,
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/projects/{project_id}", response_model=ProjectDetail)
async def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get project details with slides and messages."""
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="無効なプロジェクトIDです")

    project = db.query(SlideProject).filter(SlideProject.id == project_uuid).first()
    if not project:
        raise HTTPException(status_code=404, detail="プロジェクトが見つかりません")

    if project.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="アクセス権限がありません")

    slides = (
        db.query(SlideContent)
        .filter(SlideContent.project_id == project_uuid)
        .order_by(SlideContent.slide_number)
        .all()
    )

    messages = (
        db.query(SlideMessage)
        .filter(SlideMessage.project_id == project_uuid)
        .order_by(SlideMessage.created_at)
        .all()
    )

    return ProjectDetail(
        id=project.id,
        title=project.title,
        source_text=project.source_text,
        target_slide_count=project.target_slide_count,
        key_points=project.key_points,
        template_id=project.template_id,
        style_id=project.style_id,
        status=project.status,
        error_message=project.error_message,
        slides=[SlideOut.model_validate(s) for s in slides],
        messages=[MessageOut.model_validate(m) for m in messages],
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a project."""
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="無効なプロジェクトIDです")

    project = db.query(SlideProject).filter(SlideProject.id == project_uuid).first()
    if not project:
        raise HTTPException(status_code=404, detail="プロジェクトが見つかりません")

    if project.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="アクセス権限がありません")

    db.delete(project)
    db.commit()

    logger.info(f"Deleted project: {project_id}")


# =============================================================================
# Slide endpoints
# =============================================================================


@router.patch("/projects/{project_id}/slides/{slide_number}", response_model=SlideOut)
async def update_slide(
    project_id: str,
    slide_number: int,
    request: SlideUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a specific slide."""
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="無効なプロジェクトIDです")

    project = db.query(SlideProject).filter(SlideProject.id == project_uuid).first()
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="プロジェクトが見つかりません")

    slide = (
        db.query(SlideContent)
        .filter(
            SlideContent.project_id == project_uuid,
            SlideContent.slide_number == slide_number,
        )
        .first()
    )

    if not slide:
        raise HTTPException(status_code=404, detail="スライドが見つかりません")

    if request.title is not None:
        slide.title = request.title
    if request.content is not None:
        slide.content = request.content
    if request.speaker_notes is not None:
        slide.speaker_notes = request.speaker_notes
    if request.slide_type is not None:
        slide.slide_type = request.slide_type

    db.commit()
    db.refresh(slide)

    return SlideOut.model_validate(slide)


# =============================================================================
# Refinement endpoints
# =============================================================================


@router.post("/projects/{project_id}/refine", response_model=RefineResponse)
async def refine_project_slides(
    project_id: str,
    request: RefineRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Refine slides based on user instruction."""
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="無効なプロジェクトIDです")

    project = db.query(SlideProject).filter(SlideProject.id == project_uuid).first()
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="プロジェクトが見つかりません")

    # Get current slides
    slides = (
        db.query(SlideContent)
        .filter(SlideContent.project_id == project_uuid)
        .order_by(SlideContent.slide_number)
        .all()
    )

    current_slides = [
        {
            "slide_number": s.slide_number,
            "slide_type": s.slide_type,
            "title": s.title,
            "content": s.content,
            "speaker_notes": s.speaker_notes,
        }
        for s in slides
    ]

    # Get chat history
    messages = (
        db.query(SlideMessage)
        .filter(SlideMessage.project_id == project_uuid)
        .order_by(SlideMessage.created_at)
        .all()
    )
    chat_history = [{"role": m.role, "content": m.content} for m in messages]

    # Save user message
    user_message = SlideMessage(
        project_id=project_uuid,
        role="user",
        content=request.instruction,
    )
    db.add(user_message)
    db.commit()

    try:
        # Refine slides
        result = await refine_slides(
            current_slides=current_slides,
            instruction=request.instruction,
            chat_history=chat_history,
        )

        # Update slides
        db.query(SlideContent).filter(SlideContent.project_id == project_uuid).delete()

        new_slides = []
        for slide_data in result.get("slides", []):
            slide = SlideContent(
                project_id=project_uuid,
                slide_number=slide_data["slide_number"],
                slide_type=slide_data["slide_type"],
                title=slide_data["title"],
                content=slide_data["content"],
                speaker_notes=slide_data.get("speaker_notes", ""),
            )
            db.add(slide)
            new_slides.append(slide)

        # Save assistant message
        assistant_message = SlideMessage(
            project_id=project_uuid,
            role="assistant",
            content=f"スライドを更新しました。{len(new_slides)}枚のスライドがあります。",
        )
        db.add(assistant_message)
        db.commit()

        # Refresh slides
        for slide in new_slides:
            db.refresh(slide)

        return RefineResponse(
            message=f"スライドを更新しました",
            slides=[SlideOut.model_validate(s) for s in new_slides],
        )

    except Exception as e:
        logger.error(f"Refinement failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"スライドの更新に失敗しました: {str(e)}"
        )


# =============================================================================
# Export endpoints
# =============================================================================


@router.post("/projects/{project_id}/export")
async def export_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export project as PowerPoint file."""
    try:
        project_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="無効なプロジェクトIDです")

    project = db.query(SlideProject).filter(SlideProject.id == project_uuid).first()
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="プロジェクトが見つかりません")

    slides = (
        db.query(SlideContent)
        .filter(SlideContent.project_id == project_uuid)
        .order_by(SlideContent.slide_number)
        .all()
    )

    if not slides:
        raise HTTPException(
            status_code=400, detail="エクスポートするスライドがありません"
        )

    slide_data = [
        {
            "slide_type": s.slide_type,
            "title": s.title,
            "content": s.content,
            "speaker_notes": s.speaker_notes,
        }
        for s in slides
    ]

    # Get template path if set
    template_path = None
    if project.template_id:
        template = (
            db.query(SlideTemplate)
            .filter(SlideTemplate.id == project.template_id)
            .first()
        )
        if template:
            template_path = template.file_path

    # Get style settings if set
    style = None
    if project.style_id:
        style_record = (
            db.query(SlideStyle).filter(SlideStyle.id == project.style_id).first()
        )
        if style_record:
            style = style_record.settings

    try:
        pptx_bytes = build_pptx_from_project(
            slides=slide_data,
            template_path=template_path,
            style=style,
        )
    except Exception as e:
        logger.error(f"PPTX export failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"エクスポートに失敗しました: {str(e)}"
        )

    filename = f"{project.title}.pptx"

    return Response(
        content=pptx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# =============================================================================
# Template endpoints
# =============================================================================


@router.post(
    "/templates", response_model=TemplateOut, status_code=status.HTTP_201_CREATED
)
async def upload_template(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a PowerPoint template."""
    # Validate file type
    if not file.filename or not file.filename.endswith(".pptx"):
        raise HTTPException(
            status_code=400, detail="pptxファイルのみアップロード可能です"
        )

    content = await file.read()

    # Validate file content
    if not content.startswith(b"PK"):
        raise HTTPException(status_code=400, detail="無効なPowerPointファイルです")

    # Get slide count
    try:
        slide_count = get_slide_count(content)
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"テンプレートの解析に失敗しました: {str(e)}"
        )

    # Save file
    import uuid

    template_id = uuid.uuid4()
    upload_dir = Path(settings.UPLOAD_DIR) / "templates"
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / f"{template_id}.pptx"

    with open(file_path, "wb") as f:
        f.write(content)

    # Create template record
    template = SlideTemplate(
        id=template_id,
        user_id=current_user.id,
        name=name,
        description=description,
        file_path=str(file_path),
        original_filename=file.filename,
        slide_count=slide_count,
    )
    db.add(template)
    db.commit()
    db.refresh(template)

    return TemplateOut.model_validate(template)


@router.get("/templates", response_model=TemplateListResponse)
async def list_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List user's templates."""
    templates = (
        db.query(SlideTemplate)
        .filter(SlideTemplate.user_id == current_user.id)
        .order_by(SlideTemplate.created_at.desc())
        .all()
    )

    return TemplateListResponse(
        items=[TemplateOut.model_validate(t) for t in templates],
        total=len(templates),
    )


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a template."""
    try:
        template_uuid = UUID(template_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="無効なテンプレートIDです")

    template = db.query(SlideTemplate).filter(SlideTemplate.id == template_uuid).first()
    if not template or template.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="テンプレートが見つかりません")

    # Delete file
    try:
        Path(template.file_path).unlink(missing_ok=True)
    except Exception as e:
        logger.warning(f"Failed to delete template file: {e}")

    db.delete(template)
    db.commit()


# =============================================================================
# Style endpoints
# =============================================================================


@router.post("/styles", response_model=StyleOut, status_code=status.HTTP_201_CREATED)
async def create_style(
    request: StyleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new style."""
    # If setting as default, unset other defaults
    if request.is_default:
        db.query(SlideStyle).filter(
            SlideStyle.user_id == current_user.id,
            SlideStyle.is_default == 1,
        ).update({"is_default": 0})

    style = SlideStyle(
        user_id=current_user.id,
        name=request.name,
        description=request.description,
        settings=request.settings.model_dump(),
        is_default=1 if request.is_default else 0,
    )
    db.add(style)
    db.commit()
    db.refresh(style)

    return StyleOut(
        id=style.id,
        name=style.name,
        description=style.description,
        settings=style.settings,
        is_default=style.is_default == 1,
        created_at=style.created_at,
        updated_at=style.updated_at,
    )


@router.get("/styles", response_model=StyleListResponse)
async def list_styles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List user's styles."""
    styles = (
        db.query(SlideStyle)
        .filter(SlideStyle.user_id == current_user.id)
        .order_by(SlideStyle.created_at.desc())
        .all()
    )

    return StyleListResponse(
        items=[
            StyleOut(
                id=s.id,
                name=s.name,
                description=s.description,
                settings=s.settings,
                is_default=s.is_default == 1,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in styles
        ],
        total=len(styles),
    )


@router.patch("/styles/{style_id}", response_model=StyleOut)
async def update_style(
    style_id: str,
    request: StyleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a style."""
    try:
        style_uuid = UUID(style_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="無効なスタイルIDです")

    style = db.query(SlideStyle).filter(SlideStyle.id == style_uuid).first()
    if not style or style.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="スタイルが見つかりません")

    if request.name is not None:
        style.name = request.name
    if request.description is not None:
        style.description = request.description
    if request.settings is not None:
        style.settings = request.settings.model_dump()
    if request.is_default is not None:
        if request.is_default:
            # Unset other defaults
            db.query(SlideStyle).filter(
                SlideStyle.user_id == current_user.id,
                SlideStyle.is_default == 1,
                SlideStyle.id != style_uuid,
            ).update({"is_default": 0})
        style.is_default = 1 if request.is_default else 0

    db.commit()
    db.refresh(style)

    return StyleOut(
        id=style.id,
        name=style.name,
        description=style.description,
        settings=style.settings,
        is_default=style.is_default == 1,
        created_at=style.created_at,
        updated_at=style.updated_at,
    )


@router.delete("/styles/{style_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_style(
    style_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a style."""
    try:
        style_uuid = UUID(style_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="無効なスタイルIDです")

    style = db.query(SlideStyle).filter(SlideStyle.id == style_uuid).first()
    if not style or style.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="スタイルが見つかりません")

    db.delete(style)
    db.commit()
