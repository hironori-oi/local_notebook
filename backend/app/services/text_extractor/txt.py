from pathlib import Path
from typing import List, Tuple


def extract_text_from_txt(path: Path, encoding: str = "utf-8") -> List[Tuple[int, str]]:
    text = path.read_text(encoding=encoding)
    if not text.strip():
        return []
    return [(1, text)]
