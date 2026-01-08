import io
from pathlib import Path
from typing import List, Tuple, Union

import pdfplumber


def extract_text_from_pdf(path: Path) -> List[Tuple[int, str]]:
    """PDFから (page_number, text) のリストを返す。"""
    result: List[Tuple[int, str]] = []
    with pdfplumber.open(str(path)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                result.append((i, text))
    return result


def extract_text_from_pdf_bytes(content: bytes) -> Tuple[str, int]:
    """
    PDFバイトから全テキストとページ数を返す。

    Args:
        content: PDFファイルのバイト内容

    Returns:
        Tuple of (full_text, page_count)
    """
    full_text_parts: List[str] = []
    page_count = 0

    with pdfplumber.open(io.BytesIO(content)) as pdf:
        page_count = len(pdf.pages)
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                full_text_parts.append(f"[ページ {i}]")
                full_text_parts.append(text.strip())
                full_text_parts.append("")  # Empty line between pages

    full_text = "\n".join(full_text_parts)
    return full_text, page_count
