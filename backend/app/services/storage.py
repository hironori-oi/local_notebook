"""
Storage service abstraction for local and Supabase storage.

Provides a unified interface for file operations that works with both
local filesystem (for development) and Supabase Storage (for cloud deployment).
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from app.core.config import settings


class StorageService(ABC):
    """Abstract base class for storage operations."""

    @abstractmethod
    def upload(self, path: str, content: bytes, content_type: str) -> str:
        """
        Upload file and return the storage path or URL.

        Args:
            path: Relative path for the file
            content: File content as bytes
            content_type: MIME type of the file

        Returns:
            Storage path (local) or public URL (Supabase)
        """
        pass

    @abstractmethod
    def download(self, path: str) -> bytes:
        """
        Download file content.

        Args:
            path: Relative path or URL of the file

        Returns:
            File content as bytes
        """
        pass

    @abstractmethod
    def delete(self, path: str) -> None:
        """
        Delete a file.

        Args:
            path: Relative path or URL of the file
        """
        pass

    @abstractmethod
    def exists(self, path: str) -> bool:
        """
        Check if a file exists.

        Args:
            path: Relative path or URL of the file

        Returns:
            True if file exists, False otherwise
        """
        pass


class LocalStorageService(StorageService):
    """Local filesystem storage service."""

    def __init__(self, base_dir: str):
        """
        Initialize local storage service.

        Args:
            base_dir: Base directory for file storage
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def upload(self, path: str, content: bytes, content_type: str) -> str:
        """Upload file to local filesystem."""
        file_path = self.base_dir / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(content)
        return str(file_path)

    def download(self, path: str) -> bytes:
        """Download file from local filesystem."""
        # Handle both absolute paths and relative paths
        file_path = Path(path)
        if not file_path.is_absolute():
            file_path = self.base_dir / path
        return file_path.read_bytes()

    def delete(self, path: str) -> None:
        """Delete file from local filesystem."""
        file_path = Path(path)
        if not file_path.is_absolute():
            file_path = self.base_dir / path
        if file_path.exists():
            file_path.unlink()

    def exists(self, path: str) -> bool:
        """Check if file exists in local filesystem."""
        file_path = Path(path)
        if not file_path.is_absolute():
            file_path = self.base_dir / path
        return file_path.exists()


class SupabaseStorageService(StorageService):
    """Supabase Storage service."""

    def __init__(self, bucket: str):
        """
        Initialize Supabase storage service.

        Args:
            bucket: Supabase storage bucket name
        """
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set for Supabase storage"
            )

        from supabase import create_client

        self.client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
        self.bucket = bucket

    def _extract_path(self, path: str) -> str:
        """
        Extract storage path from URL or return path as-is.

        Args:
            path: Full URL or relative path

        Returns:
            Clean relative path for Supabase storage
        """
        if path.startswith("http"):
            from urllib.parse import urlparse

            parsed = urlparse(path)
            # Supabase URL format: /storage/v1/object/public/{bucket}/{path}
            path_parts = parsed.path.split(f"/public/{self.bucket}/")
            if len(path_parts) > 1:
                return path_parts[1].lstrip("/")
            # Fallback: try to extract filename from URL
            return parsed.path.split("/")[-1]
        return path.lstrip("/")

    def upload(self, path: str, content: bytes, content_type: str) -> str:
        """Upload file to Supabase Storage."""
        path = path.lstrip("/")
        self.client.storage.from_(self.bucket).upload(
            path, content, {"content-type": content_type}
        )
        return self.client.storage.from_(self.bucket).get_public_url(path)

    def download(self, path: str) -> bytes:
        """Download file from Supabase Storage."""
        path = self._extract_path(path)
        return self.client.storage.from_(self.bucket).download(path)

    def delete(self, path: str) -> None:
        """Delete file from Supabase Storage."""
        path = self._extract_path(path)
        self.client.storage.from_(self.bucket).remove([path])

    def exists(self, path: str) -> bool:
        """Check if file exists in Supabase Storage."""
        try:
            path = self._extract_path(path)
            # Use list API instead of downloading the entire file
            # Split path into parent directory and filename
            path_obj = Path(path)
            parent = str(path_obj.parent) if path_obj.parent != Path(".") else ""
            filename = path_obj.name

            result = self.client.storage.from_(self.bucket).list(parent)
            return any(f.get("name") == filename for f in result)
        except Exception:
            return False


# Storage service instances cache
_storage_services: dict[str, StorageService] = {}


def get_storage_service(bucket_type: str = "uploads") -> StorageService:
    """
    Factory function to get the appropriate storage service.

    Args:
        bucket_type: Type of bucket ('uploads', 'generated', 'audio')

    Returns:
        StorageService instance (LocalStorageService or SupabaseStorageService)
    """
    cache_key = f"{settings.STORAGE_PROVIDER}:{bucket_type}"

    if cache_key not in _storage_services:
        if settings.STORAGE_PROVIDER == "supabase":
            bucket_map = {
                "uploads": settings.SUPABASE_STORAGE_BUCKET,
                "generated": "generated",
                "audio": "audio-temp",
            }
            bucket_name = bucket_map.get(bucket_type, bucket_type)
            _storage_services[cache_key] = SupabaseStorageService(bucket_name)
        else:
            dir_map = {
                "uploads": settings.UPLOAD_DIR,
                "generated": settings.GENERATED_FILES_DIR,
                "audio": settings.TEMP_AUDIO_DIR,
            }
            base_dir = dir_map.get(bucket_type, settings.UPLOAD_DIR)
            _storage_services[cache_key] = LocalStorageService(base_dir)

    return _storage_services[cache_key]
