from pathlib import Path
from typing import List, Tuple
from docx import Document


def extract_text_from_docx(path: Path) -> List[Tuple[int, str]]:
    """Word(docx)から (page_number, text) のリストを返す。
    ※ page_number は 1 固定（厳密なページは取れないため）
    """
    doc = Document(str(path))
    texts = []
    for para in doc.paragraphs:
        if para.text.strip():
            texts.append(para.text)
    joined = "\n".join(texts)
    if not joined.strip():
        return []
    return [(1, joined)]
