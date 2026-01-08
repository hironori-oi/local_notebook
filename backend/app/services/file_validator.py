"""
File validation utilities for secure file uploads.

This module provides functions to validate uploaded files by checking:
- File extension
- MIME type (magic bytes)
- File size
- Content safety
"""

import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


# Magic byte signatures for supported file types
# Format: { extension: (magic_bytes, offset, description) }
FILE_SIGNATURES: Dict[str, list[Tuple[bytes, int, str]]] = {
    "pdf": [
        (b"%PDF", 0, "PDF document"),
    ],
    "docx": [
        # DOCX files are ZIP archives starting with PK signature
        (b"PK\x03\x04", 0, "DOCX/Office Open XML"),
        (b"PK\x05\x06", 0, "DOCX/Office Open XML (empty)"),
        (b"PK\x07\x08", 0, "DOCX/Office Open XML (spanned)"),
    ],
    "pptx": [
        # PPTX files are ZIP archives starting with PK signature
        (b"PK\x03\x04", 0, "PPTX/Office Open XML"),
        (b"PK\x05\x06", 0, "PPTX/Office Open XML (empty)"),
        (b"PK\x07\x08", 0, "PPTX/Office Open XML (spanned)"),
    ],
    "txt": [],  # Text files don't have magic bytes
    "md": [],   # Markdown files don't have magic bytes
}

# MIME types for supported file types
MIME_TYPES: Dict[str, list[str]] = {
    "pdf": ["application/pdf"],
    "docx": [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",  # DOCX is actually a ZIP file
    ],
    "pptx": [
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/zip",  # PPTX is actually a ZIP file
    ],
    "txt": ["text/plain"],
    "md": ["text/plain", "text/markdown"],
}

# Dangerous patterns that should not appear in text files
# These could indicate malicious content injection
DANGEROUS_PATTERNS = [
    b"<script",
    b"javascript:",
    b"vbscript:",
    b"data:text/html",
    b"<?php",
    b"<%",
]


class FileValidationError(Exception):
    """Raised when file validation fails."""

    def __init__(self, message: str, error_code: str = "VALIDATION_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


def validate_file_extension(filename: str, allowed_extensions: set[str]) -> str:
    """
    Validate and return the file extension.

    Args:
        filename: Original filename
        allowed_extensions: Set of allowed extensions (without dot)

    Returns:
        Lowercase file extension without dot

    Raises:
        FileValidationError: If extension is not allowed
    """
    if not filename:
        raise FileValidationError(
            "ファイル名が空です",
            error_code="EMPTY_FILENAME"
        )

    suffix = Path(filename).suffix.lower()
    if not suffix:
        raise FileValidationError(
            "ファイル拡張子がありません",
            error_code="NO_EXTENSION"
        )

    extension = suffix.lstrip(".")
    if extension not in allowed_extensions:
        raise FileValidationError(
            f"サポートされていないファイル形式です: {extension}",
            error_code="UNSUPPORTED_TYPE"
        )

    return extension


def validate_magic_bytes(content: bytes, file_type: str) -> bool:
    """
    Validate file content against known magic byte signatures.

    Args:
        content: File content as bytes
        file_type: Expected file type (pdf, docx, txt, md)

    Returns:
        True if valid, False otherwise

    Note:
        Text files (txt, md) always return True as they don't have magic bytes
    """
    signatures = FILE_SIGNATURES.get(file_type, [])

    # Text files don't have magic bytes - validate differently
    if not signatures:
        return True

    for magic_bytes, offset, description in signatures:
        if len(content) >= offset + len(magic_bytes):
            if content[offset:offset + len(magic_bytes)] == magic_bytes:
                logger.debug(f"File matched signature: {description}")
                return True

    return False


def validate_text_content_safety(content: bytes) -> Tuple[bool, Optional[str]]:
    """
    Check text file content for potentially dangerous patterns.

    Args:
        content: File content as bytes

    Returns:
        Tuple of (is_safe, error_message)
    """
    content_lower = content.lower()

    for pattern in DANGEROUS_PATTERNS:
        if pattern.lower() in content_lower:
            return False, f"潜在的に危険なコンテンツが検出されました: {pattern.decode('utf-8', errors='ignore')}"

    return True, None


def validate_file_size(content: bytes, max_size_mb: int) -> bool:
    """
    Validate file size against maximum allowed size.

    Args:
        content: File content as bytes
        max_size_mb: Maximum allowed size in megabytes

    Returns:
        True if valid

    Raises:
        FileValidationError: If file is too large
    """
    max_bytes = max_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise FileValidationError(
            f"ファイルサイズが大きすぎます（最大 {max_size_mb}MB）",
            error_code="FILE_TOO_LARGE"
        )
    return True


def validate_uploaded_file(
    filename: str,
    content: bytes,
    allowed_extensions: set[str],
    max_size_mb: int,
) -> str:
    """
    Comprehensive file validation.

    Args:
        filename: Original filename
        content: File content as bytes
        allowed_extensions: Set of allowed extensions
        max_size_mb: Maximum allowed size in MB

    Returns:
        Validated file extension

    Raises:
        FileValidationError: If any validation fails
    """
    # 1. Validate extension
    file_type = validate_file_extension(filename, allowed_extensions)

    # 2. Validate size
    validate_file_size(content, max_size_mb)

    # 3. Validate magic bytes
    if not validate_magic_bytes(content, file_type):
        logger.warning(
            f"File {filename} has invalid magic bytes for type {file_type}"
        )
        raise FileValidationError(
            f"ファイルの内容が拡張子（{file_type}）と一致しません",
            error_code="INVALID_CONTENT"
        )

    # 4. For text files, check for dangerous content
    if file_type in ("txt", "md"):
        is_safe, error_msg = validate_text_content_safety(content)
        if not is_safe:
            logger.warning(f"Dangerous content detected in {filename}: {error_msg}")
            raise FileValidationError(
                error_msg or "危険なコンテンツが検出されました",
                error_code="DANGEROUS_CONTENT"
            )

    logger.info(f"File {filename} passed all validations")
    return file_type
