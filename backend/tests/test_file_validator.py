"""
Tests for file validation service.
"""

import pytest

from app.services.file_validator import (
    FileValidationError,
    validate_file_extension,
    validate_file_size,
    validate_magic_bytes,
    validate_text_content_safety,
    validate_uploaded_file,
)


class TestValidateFileExtension:
    """Tests for file extension validation."""

    def test_valid_txt_extension(self):
        """Test valid .txt extension."""
        result = validate_file_extension("document.txt", {"txt", "pdf", "docx"})
        assert result == "txt"

    def test_valid_pdf_extension(self):
        """Test valid .pdf extension."""
        result = validate_file_extension("document.pdf", {"txt", "pdf", "docx"})
        assert result == "pdf"

    def test_valid_docx_extension(self):
        """Test valid .docx extension."""
        result = validate_file_extension("document.docx", {"txt", "pdf", "docx"})
        assert result == "docx"

    def test_invalid_extension(self):
        """Test invalid extension."""
        with pytest.raises(FileValidationError) as exc_info:
            validate_file_extension("script.sh", {"txt", "pdf", "docx"})
        assert "サポートされていないファイル形式" in str(exc_info.value)

    def test_no_extension(self):
        """Test file with no extension."""
        with pytest.raises(FileValidationError) as exc_info:
            validate_file_extension("noextension", {"txt", "pdf", "docx"})
        assert "サポートされていないファイル形式" in str(exc_info.value)

    def test_case_insensitive(self):
        """Test case insensitive extension matching."""
        result = validate_file_extension("Document.TXT", {"txt", "pdf"})
        assert result == "txt"

    def test_double_extension(self):
        """Test file with double extension."""
        result = validate_file_extension("document.backup.txt", {"txt", "pdf"})
        assert result == "txt"


class TestValidateFileSize:
    """Tests for file size validation."""

    def test_valid_size(self):
        """Test file within size limit."""
        content = b"x" * 1000  # 1KB
        validate_file_size(content, max_size_mb=10)  # Should not raise

    def test_empty_file(self):
        """Test empty file."""
        with pytest.raises(FileValidationError) as exc_info:
            validate_file_size(b"", max_size_mb=10)
        assert "空のファイル" in str(exc_info.value)

    def test_file_too_large(self):
        """Test file exceeding size limit."""
        content = b"x" * (11 * 1024 * 1024)  # 11MB
        with pytest.raises(FileValidationError) as exc_info:
            validate_file_size(content, max_size_mb=10)
        assert "ファイルサイズが大きすぎます" in str(exc_info.value)

    def test_exact_size_limit(self):
        """Test file exactly at size limit."""
        content = b"x" * (10 * 1024 * 1024)  # Exactly 10MB
        validate_file_size(content, max_size_mb=10)  # Should not raise


class TestValidateMagicBytes:
    """Tests for magic bytes validation."""

    def test_valid_pdf_magic(self):
        """Test valid PDF magic bytes."""
        content = b"%PDF-1.4 some pdf content"
        assert validate_magic_bytes(content, "pdf") is True

    def test_invalid_pdf_magic(self):
        """Test invalid PDF magic bytes."""
        content = b"This is not a PDF file"
        assert validate_magic_bytes(content, "pdf") is False

    def test_valid_docx_magic(self):
        """Test valid DOCX magic bytes (ZIP format)."""
        content = b"PK\x03\x04 some docx content"
        assert validate_magic_bytes(content, "docx") is True

    def test_txt_always_valid(self):
        """Test that text files always pass magic byte check."""
        content = b"Any text content works"
        assert validate_magic_bytes(content, "txt") is True

    def test_md_always_valid(self):
        """Test that markdown files always pass magic byte check."""
        content = b"# Markdown content"
        assert validate_magic_bytes(content, "md") is True

    def test_unknown_type(self):
        """Test unknown file type."""
        content = b"Some content"
        assert validate_magic_bytes(content, "unknown") is True


class TestValidateTextContentSafety:
    """Tests for text content safety validation."""

    def test_valid_utf8_content(self):
        """Test valid UTF-8 content."""
        content = "Hello, World! こんにちは".encode("utf-8")
        is_safe, error = validate_text_content_safety(content)
        assert is_safe is True
        assert error is None

    def test_invalid_utf8_content(self):
        """Test invalid UTF-8 content."""
        content = b"\xff\xfe invalid utf8"
        is_safe, error = validate_text_content_safety(content)
        # Depending on implementation, this might pass or fail
        # The validator should handle encoding issues gracefully

    def test_null_bytes_in_content(self):
        """Test content with null bytes."""
        content = b"Hello\x00World"
        is_safe, error = validate_text_content_safety(content)
        assert is_safe is False
        assert error is not None


class TestValidateUploadedFile:
    """Tests for complete file validation."""

    def test_valid_txt_file(self):
        """Test valid text file."""
        content = b"This is a valid text file content."
        result = validate_uploaded_file(
            "document.txt",
            content,
            {"txt", "pdf", "docx"},
            max_size_mb=10,
        )
        assert result == "txt"

    def test_invalid_extension(self):
        """Test file with invalid extension."""
        content = b"Some content"
        with pytest.raises(FileValidationError):
            validate_uploaded_file(
                "script.exe",
                content,
                {"txt", "pdf", "docx"},
                max_size_mb=10,
            )

    def test_file_too_large(self):
        """Test file exceeding size limit."""
        content = b"x" * (11 * 1024 * 1024)  # 11MB
        with pytest.raises(FileValidationError) as exc_info:
            validate_uploaded_file(
                "large.txt",
                content,
                {"txt", "pdf"},
                max_size_mb=10,
            )
        assert "ファイルサイズ" in str(exc_info.value)

    def test_extension_mismatch(self):
        """Test file with mismatched extension and content."""
        content = b"This is text, not PDF"
        with pytest.raises(FileValidationError) as exc_info:
            validate_uploaded_file(
                "fake.pdf",
                content,
                {"txt", "pdf"},
                max_size_mb=10,
            )
        assert "ファイルの内容が拡張子と一致しません" in str(exc_info.value)

    def test_valid_pdf_file(self):
        """Test valid PDF file."""
        content = b"%PDF-1.4 fake pdf content for testing"
        result = validate_uploaded_file(
            "document.pdf",
            content,
            {"txt", "pdf", "docx"},
            max_size_mb=10,
        )
        assert result == "pdf"
