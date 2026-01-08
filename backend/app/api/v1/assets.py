"""
Assets API endpoints for serving generated files.

This module provides endpoints to serve generated images and other assets.
"""
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.config import settings

router = APIRouter(prefix="/assets", tags=["assets"])

# Directory for generated images
IMAGE_BASE_DIR = Path(settings.GENERATED_FILES_DIR) / "images"


@router.get("/images/{filename}")
async def get_image(filename: str):
    """
    Serve a generated image file.

    Args:
        filename: The image filename (e.g., "infographic_uuid_section_1.png")

    Returns:
        FileResponse with the image

    Raises:
        HTTPException: 404 if image not found, 403 if path traversal attempted
    """
    # Security: prevent path traversal attacks
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=403, detail="アクセスが拒否されました")

    file_path = IMAGE_BASE_DIR / filename

    # Verify the file is within the allowed directory
    try:
        file_path = file_path.resolve()
        base_path = IMAGE_BASE_DIR.resolve()
        if not str(file_path).startswith(str(base_path)):
            raise HTTPException(status_code=403, detail="アクセスが拒否されました")
    except Exception:
        raise HTTPException(status_code=403, detail="アクセスが拒否されました")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="画像が見つかりません")

    return FileResponse(
        path=file_path,
        media_type="image/png",
        filename=filename,
    )


@router.get("/health")
async def assets_health():
    """Check if the assets directory is accessible."""
    IMAGE_BASE_DIR.mkdir(parents=True, exist_ok=True)
    return {
        "status": "healthy",
        "image_directory": str(IMAGE_BASE_DIR),
        "directory_exists": IMAGE_BASE_DIR.exists(),
    }
