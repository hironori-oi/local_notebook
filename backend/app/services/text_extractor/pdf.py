from pathlib import Path
from typing import List, Tuple
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
