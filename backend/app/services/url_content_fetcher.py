"""
URL Content Fetcher service for fetching and extracting text from URLs.

This service handles:
1. Fetching content from government and other URLs
2. HTML text extraction using BeautifulSoup
3. PDF text extraction (if URL points to PDF)
4. Error handling with retry logic
"""

import logging
import re
from io import BytesIO
from typing import Optional, Tuple

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

# Check if HTTP/2 support is available
try:
    import h2  # noqa: F401
    HTTP2_AVAILABLE = True
except ImportError:
    HTTP2_AVAILABLE = False

# Maximum content size to fetch (10MB)
MAX_CONTENT_SIZE = 10 * 1024 * 1024

# Request timeout in seconds (increased for government PDFs)
REQUEST_TIMEOUT = 120.0  # 2 minutes for slow government servers

# User-Agent for requests (to avoid being blocked)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# HTML tags to remove (usually contain navigation, ads, etc.)
TAGS_TO_REMOVE = [
    "script",
    "style",
    "nav",
    "header",
    "footer",
    "aside",
    "noscript",
    "iframe",
    "form",
    "button",
    "input",
]

# HTML tags that indicate main content
MAIN_CONTENT_SELECTORS = [
    "main",
    "article",
    "[role='main']",
    ".main-content",
    ".content",
    "#content",
    "#main",
    ".article-body",
    ".post-content",
]


# =============================================================================
# URL Content Fetcher
# =============================================================================


class URLContentFetchError(Exception):
    """Exception raised when URL content fetching fails."""

    pass


async def fetch_url_content(url: str) -> Tuple[str, str]:
    """
    Fetch and extract text content from a URL.

    Supports:
    - HTML pages (extracts main text content)
    - PDF files (extracts text using pdfplumber)

    Args:
        url: URL to fetch content from

    Returns:
        Tuple of (extracted_text, content_type)

    Raises:
        URLContentFetchError: If fetching or extraction fails
    """
    if not url or not url.strip():
        raise URLContentFetchError("URLが空です")

    url = url.strip()

    # Validate URL format
    if not url.startswith(("http://", "https://")):
        raise URLContentFetchError(f"無効なURL形式です: {url}")

    logger.info(f"Fetching content from URL: {url} (HTTP/2: {HTTP2_AVAILABLE})")

    # Extract domain for Referer header (helps with government site access)
    from urllib.parse import urlparse
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    try:
        # Configure separate timeouts for different operations
        timeout = httpx.Timeout(
            connect=30.0,      # 30s to establish connection
            read=REQUEST_TIMEOUT,  # 120s to read response (for large PDFs)
            write=30.0,
            pool=30.0,
        )

        # Build browser-like headers (important for government sites)
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf;q=0.8,image/webp,*/*;q=0.7",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": base_url + "/",  # Pretend we came from the same site
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }

        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers=headers,
            http2=HTTP2_AVAILABLE,  # Enable HTTP/2 if h2 package is available
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

            # Check content size
            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > MAX_CONTENT_SIZE:
                raise URLContentFetchError(
                    f"コンテンツサイズが大きすぎます: {int(content_length) / 1024 / 1024:.1f}MB"
                )

            content_type = response.headers.get("content-type", "").lower()
            logger.info(f"Content-Type: {content_type}")

            # Handle PDF content
            if "application/pdf" in content_type or url.lower().endswith(".pdf"):
                text = await _extract_pdf_text(response.content)
                return text, "application/pdf"

            # Handle HTML content
            if "text/html" in content_type or not content_type:
                text = _extract_html_text(response.text, url)
                return text, "text/html"

            # Handle plain text
            if "text/plain" in content_type:
                return response.text, "text/plain"

            # Try to extract as HTML for other content types
            try:
                text = _extract_html_text(response.text, url)
                return text, content_type
            except Exception:
                raise URLContentFetchError(
                    f"サポートされていないコンテンツタイプです: {content_type}"
                )

    except httpx.TimeoutException:
        raise URLContentFetchError(f"リクエストがタイムアウトしました: {url}")
    except httpx.HTTPStatusError as e:
        raise URLContentFetchError(f"HTTPエラー {e.response.status_code}: {url}")
    except httpx.RequestError as e:
        raise URLContentFetchError(f"リクエストエラー: {str(e)}")
    except URLContentFetchError:
        raise
    except Exception as e:
        logger.error(f"URL fetch error: {e}", exc_info=True)
        raise URLContentFetchError(f"コンテンツ取得に失敗しました: {str(e)}")


def _extract_html_text(html: str, url: str = "") -> str:
    """
    Extract main text content from HTML.

    Attempts to find the main content area first, then falls back
    to extracting all text if no main content is found.

    Args:
        html: HTML string
        url: Original URL (for logging)

    Returns:
        Extracted text content
    """
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")

    # Remove unwanted tags
    for tag_name in TAGS_TO_REMOVE:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # Try to find main content area
    main_content = None
    for selector in MAIN_CONTENT_SELECTORS:
        main_content = soup.select_one(selector)
        if main_content:
            logger.debug(f"Found main content with selector: {selector}")
            break

    # Use main content if found, otherwise use body or entire document
    if main_content:
        target = main_content
    elif soup.body:
        target = soup.body
    else:
        target = soup

    # Extract text with proper spacing
    text = _extract_text_with_structure(target)

    # Clean up the text
    text = _clean_extracted_text(text)

    logger.info(f"Extracted {len(text)} characters from HTML")
    return text


def _extract_text_with_structure(element) -> str:
    """
    Extract text from BeautifulSoup element while preserving some structure.

    Args:
        element: BeautifulSoup element

    Returns:
        Extracted text with preserved paragraph breaks
    """
    texts = []

    for child in element.descendants:
        if child.name in [
            "p",
            "div",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "li",
            "tr",
            "br",
        ]:
            texts.append("\n")
        elif child.name is None and child.string:
            text = child.string.strip()
            if text:
                texts.append(text + " ")

    return "".join(texts)


def _clean_extracted_text(text: str) -> str:
    """
    Clean up extracted text.

    Args:
        text: Raw extracted text

    Returns:
        Cleaned text
    """
    # Normalize whitespace
    text = re.sub(r"[ \t]+", " ", text)

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove excessive newlines (more than 2)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Remove leading/trailing whitespace from lines
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    # Remove leading/trailing whitespace from entire text
    text = text.strip()

    return text


async def _extract_pdf_text(pdf_content: bytes) -> str:
    """
    Extract text from PDF content.

    Uses pdfplumber for better extraction quality.

    Args:
        pdf_content: PDF file content as bytes

    Returns:
        Extracted text

    Raises:
        URLContentFetchError: If PDF extraction fails
    """
    try:
        import pdfplumber
    except ImportError:
        logger.warning("pdfplumber not installed, trying PyPDF2")
        return await _extract_pdf_text_pypdf2(pdf_content)

    try:
        texts = []
        with pdfplumber.open(BytesIO(pdf_content)) as pdf:
            for i, page in enumerate(pdf.pages):
                try:
                    text = page.extract_text()
                    if text:
                        texts.append(f"--- ページ {i + 1} ---\n{text}")
                except Exception as e:
                    logger.warning(f"Failed to extract page {i + 1}: {e}")
                    continue

        if not texts:
            raise URLContentFetchError("PDFからテキストを抽出できませんでした")

        result = "\n\n".join(texts)
        logger.info(
            f"Extracted {len(result)} characters from PDF ({len(pdf.pages)} pages)"
        )
        return result

    except URLContentFetchError:
        raise
    except Exception as e:
        logger.error(f"PDF extraction error: {e}", exc_info=True)
        raise URLContentFetchError(f"PDF解析に失敗しました: {str(e)}")


async def _extract_pdf_text_pypdf2(pdf_content: bytes) -> str:
    """
    Fallback PDF extraction using PyPDF2.

    Args:
        pdf_content: PDF file content as bytes

    Returns:
        Extracted text
    """
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        raise URLContentFetchError(
            "PDF抽出ライブラリがインストールされていません (pdfplumber or PyPDF2)"
        )

    try:
        texts = []
        reader = PdfReader(BytesIO(pdf_content))
        for i, page in enumerate(reader.pages):
            try:
                text = page.extract_text()
                if text:
                    texts.append(f"--- ページ {i + 1} ---\n{text}")
            except Exception as e:
                logger.warning(f"Failed to extract page {i + 1}: {e}")
                continue

        if not texts:
            raise URLContentFetchError("PDFからテキストを抽出できませんでした")

        result = "\n\n".join(texts)
        logger.info(f"Extracted {len(result)} characters from PDF (PyPDF2)")
        return result

    except URLContentFetchError:
        raise
    except Exception as e:
        logger.error(f"PyPDF2 extraction error: {e}", exc_info=True)
        raise URLContentFetchError(f"PDF解析に失敗しました: {str(e)}")


async def fetch_url_with_retry(
    url: str,
    max_retries: int = 3,
    initial_delay: float = 2.0,
) -> Tuple[str, str]:
    """
    Fetch URL content with retry logic and exponential backoff.

    Args:
        url: URL to fetch
        max_retries: Maximum number of retries (default: 3 = 4 total attempts)
        initial_delay: Initial delay between retries in seconds (doubles each retry)

    Returns:
        Tuple of (extracted_text, content_type)

    Raises:
        URLContentFetchError: If all retries fail
    """
    import asyncio
    import random

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            return await fetch_url_content(url)
        except URLContentFetchError as e:
            last_error = e
            if attempt < max_retries:
                # Exponential backoff with jitter
                delay = initial_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(
                    f"URL fetch attempt {attempt + 1} failed, retrying in {delay:.1f}s: {e}"
                )
                await asyncio.sleep(delay)
            else:
                logger.error(f"URL fetch failed after {max_retries + 1} attempts: {e}")

    raise last_error or URLContentFetchError("URL取得に失敗しました")
