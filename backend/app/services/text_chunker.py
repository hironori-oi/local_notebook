"""
Text Chunker Service - Semantic text splitting with overlap.

This module provides intelligent text chunking that:
- Respects natural text boundaries (paragraphs, sentences)
- Maintains overlap between chunks for better retrieval
- Handles Japanese and English text appropriately
"""
from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class ChunkResult:
    """Result of chunking a page of text."""
    content: str
    page_number: int
    chunk_index: int


def find_split_point(text: str, max_pos: int, separators: List[str]) -> int:
    """
    Find the best split point within text, preferring natural boundaries.

    Args:
        text: The text to find a split point in
        max_pos: Maximum position to search up to
        separators: List of separators in order of preference

    Returns:
        The best position to split at
    """
    if max_pos >= len(text):
        return len(text)

    # Try each separator in order of preference
    for sep in separators:
        # Search backwards from max_pos for the separator
        pos = text.rfind(sep, 0, max_pos)
        if pos > max_pos * 0.5:  # Only accept if we're past halfway
            return pos + len(sep)

    # No good separator found, just split at max_pos
    return max_pos


def chunk_text_with_overlap(
    text: str,
    chunk_size: int = 2000,
    overlap: int = 200,
    separators: List[str] = None,
) -> List[str]:
    """
    Split text into overlapping chunks while respecting natural boundaries.

    This function implements semantic chunking that:
    - Prefers splitting at paragraph or sentence boundaries
    - Maintains overlap between consecutive chunks
    - Handles both Japanese and English text

    Args:
        text: The text to chunk
        chunk_size: Target size for each chunk (default: 2000 chars)
        overlap: Number of characters to overlap between chunks (default: 200)
        separators: List of separators in order of preference.
                   Default: ["\n\n", "\n", "。", ".", "！", "？", "!", "?", " "]

    Returns:
        List of text chunks

    Example:
        >>> text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        >>> chunks = chunk_text_with_overlap(text, chunk_size=30, overlap=10)
        >>> len(chunks)
        2
    """
    if separators is None:
        # Default separators: paragraphs, newlines, Japanese/English sentence ends, spaces
        separators = ["\n\n", "\n", "。", ".", "！", "？", "!", "?", " "]

    if not text or not text.strip():
        return []

    # Normalize whitespace
    text = text.strip()

    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        # Calculate end position
        end = start + chunk_size

        if end >= len(text):
            # Last chunk - take everything remaining
            chunks.append(text[start:].strip())
            break

        # Find the best split point
        split_pos = find_split_point(text, end, separators)

        # Extract chunk
        chunk = text[start:split_pos].strip()
        if chunk:
            chunks.append(chunk)

        # Move start position back by overlap amount
        start = split_pos - overlap
        if start < 0:
            start = split_pos

        # Safety check to prevent infinite loop
        if start >= len(text) or (len(chunks) > 0 and start <= (split_pos - chunk_size)):
            break

    return chunks


def chunk_pages_with_overlap(
    page_texts: List[Tuple[int, str]],
    chunk_size: int = 2000,
    overlap: int = 200,
    separators: List[str] = None,
) -> List[ChunkResult]:
    """
    Process multiple pages and create overlapping chunks.

    This function processes page-by-page text and creates chunks while:
    - Tracking page numbers for each chunk
    - Maintaining global chunk indices
    - Applying overlap within each page

    Args:
        page_texts: List of (page_number, text) tuples
        chunk_size: Target size for each chunk (default: 2000 chars)
        overlap: Number of characters to overlap (default: 200)
        separators: List of separators in order of preference

    Returns:
        List of ChunkResult objects with content, page_number, and chunk_index
    """
    results: List[ChunkResult] = []
    chunk_index = 0

    for page_number, text in page_texts:
        if not text or not text.strip():
            continue

        page_chunks = chunk_text_with_overlap(
            text=text,
            chunk_size=chunk_size,
            overlap=overlap,
            separators=separators,
        )

        for chunk_content in page_chunks:
            if chunk_content.strip():
                results.append(ChunkResult(
                    content=chunk_content,
                    page_number=page_number,
                    chunk_index=chunk_index,
                ))
                chunk_index += 1

    return results
