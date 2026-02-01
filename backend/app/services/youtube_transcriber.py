"""
YouTube Transcription Service.

This module handles:
- YouTube video ID extraction from URLs
- Audio extraction using yt-dlp
- Speech-to-text transcription via Whisper server
- Text formatting using local LLM
"""

import asyncio
import base64
import logging
import os
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional
from uuid import UUID

import httpx
import yt_dlp
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.transcription import Transcription
from app.services.llm_client import call_llm

logger = logging.getLogger(__name__)

# Thread pool for blocking yt-dlp operations
_executor = ThreadPoolExecutor(max_workers=2)

# Cache for decoded cookies file path
_cookies_file_path: Optional[str] = None


def _get_cookies_file() -> Optional[str]:
    """
    Get the path to YouTube cookies file.

    Decodes cookies from YOUTUBE_COOKIES_BASE64 environment variable
    and writes to a temporary file if not already done.

    Returns:
        Path to cookies file, or None if not configured
    """
    global _cookies_file_path

    # Return cached path if already created
    if _cookies_file_path and os.path.exists(_cookies_file_path):
        return _cookies_file_path

    # Check for base64-encoded cookies in environment
    cookies_base64 = os.environ.get("YOUTUBE_COOKIES_BASE64")
    if not cookies_base64:
        logger.debug("YOUTUBE_COOKIES_BASE64 not set, proceeding without cookies")
        return None

    try:
        # Decode base64 cookies
        cookies_content = base64.b64decode(cookies_base64).decode("utf-8")

        # Write to a temporary file that persists for the process lifetime
        cookies_dir = Path(settings.TEMP_AUDIO_DIR)
        cookies_dir.mkdir(parents=True, exist_ok=True)
        cookies_path = cookies_dir / "youtube_cookies.txt"

        with open(cookies_path, "w", encoding="utf-8") as f:
            f.write(cookies_content)

        _cookies_file_path = str(cookies_path)
        logger.info(f"YouTube cookies file created: {_cookies_file_path}")
        return _cookies_file_path

    except Exception as e:
        logger.error(f"Failed to decode YouTube cookies: {e}")
        return None


def extract_video_id(url: str) -> Optional[str]:
    """
    Extract YouTube video ID from various URL formats.

    Supported formats:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/shorts/VIDEO_ID
    - https://www.youtube.com/live/VIDEO_ID

    Args:
        url: YouTube URL

    Returns:
        Video ID string or None if not found
    """
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/|youtube\.com/live/)([a-zA-Z0-9_-]{11})",
        r"youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def _download_audio_sync(url: str, output_path: str) -> dict:
    """
    Synchronous function to download audio from YouTube using yt-dlp.

    This runs in a thread pool to avoid blocking the async event loop.

    Args:
        url: YouTube URL
        output_path: Path to save the audio file (without extension)

    Returns:
        Dict with video info (title, duration, etc.)
    """
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_path,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
    }

    # Add cookies file if available (helps bypass YouTube bot detection)
    cookies_file = _get_cookies_file()
    if cookies_file:
        ydl_opts["cookiefile"] = cookies_file
        logger.info("Using YouTube cookies for authentication")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return {
            "title": info.get("title"),
            "duration": info.get("duration", 0),
            "uploader": info.get("uploader"),
        }


async def download_youtube_audio(url: str, video_id: str) -> tuple[str, dict]:
    """
    Download audio from YouTube video asynchronously.

    Args:
        url: YouTube URL
        video_id: Video ID for filename

    Returns:
        Tuple of (audio_file_path, video_info)

    Raises:
        ValueError: If video duration exceeds limit
        RuntimeError: If download fails
    """
    # Ensure temp directory exists
    Path(settings.TEMP_AUDIO_DIR).mkdir(parents=True, exist_ok=True)

    output_path = os.path.join(settings.TEMP_AUDIO_DIR, f"{video_id}")

    loop = asyncio.get_event_loop()

    try:
        info = await loop.run_in_executor(
            _executor, _download_audio_sync, url, output_path
        )
    except Exception as e:
        logger.error(f"Failed to download audio: {e}")
        raise RuntimeError(f"Failed to download audio: {str(e)}")

    # Check duration limit
    duration_minutes = info.get("duration", 0) / 60
    if duration_minutes > settings.MAX_VIDEO_DURATION_MINUTES:
        # Clean up downloaded file
        audio_path = f"{output_path}.mp3"
        if os.path.exists(audio_path):
            os.unlink(audio_path)
        raise ValueError(
            f"Video duration ({duration_minutes:.1f} minutes) exceeds "
            f"maximum allowed ({settings.MAX_VIDEO_DURATION_MINUTES} minutes)"
        )

    audio_path = f"{output_path}.mp3"
    if not os.path.exists(audio_path):
        raise RuntimeError(f"Audio file not found after download: {audio_path}")

    logger.info(f"Downloaded audio: {audio_path} ({info.get('duration', 0)}s)")

    return audio_path, info


def is_whisper_configured() -> bool:
    """Check if Whisper server is configured."""
    return bool(settings.WHISPER_SERVER_URL)


async def transcribe_audio(audio_path: str, language: str = "ja") -> str:
    """
    Send audio file to Whisper server for transcription.

    Args:
        audio_path: Path to the audio file
        language: Language code for transcription

    Returns:
        Raw transcription text

    Raises:
        RuntimeError: If transcription fails or Whisper server not configured
    """
    if not settings.WHISPER_SERVER_URL:
        raise RuntimeError(
            "Whisper server is not configured. "
            "Set WHISPER_SERVER_URL in environment variables."
        )

    # Long timeout for processing lengthy videos (144 min video may take 30-60+ min)
    async with httpx.AsyncClient(timeout=3600.0) as client:
        try:
            with open(audio_path, "rb") as f:
                files = {"file": (os.path.basename(audio_path), f, "audio/mpeg")}
                data = {"language": language}

                logger.info(f"Sending audio to Whisper server: {audio_path}")

                response = await client.post(
                    f"{settings.WHISPER_SERVER_URL}/transcribe",
                    files=files,
                    data=data,
                )
                response.raise_for_status()

                result = response.json()
                return result.get("text", "")

        except httpx.ConnectError as e:
            logger.error(f"Failed to connect to Whisper server: {e}")
            raise RuntimeError(f"Whisper server is not available: {str(e)}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Whisper server error: {e.response.status_code}")
            raise RuntimeError(f"Whisper server error: {e.response.text}")
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise RuntimeError(f"Transcription failed: {str(e)}")


async def format_transcript_with_llm(raw_text: str) -> str:
    """
    Format raw transcription text using LLM.

    Cleans up the text by:
    - Adding proper punctuation
    - Fixing sentence boundaries
    - Removing filler words
    - Adding paragraph breaks

    Args:
        raw_text: Raw transcription text from Whisper

    Returns:
        Formatted text
    """
    if not raw_text or len(raw_text.strip()) < 10:
        return raw_text

    messages = [
        {
            "role": "system",
            "content": (
                "あなたは文字起こしテキストを整形するアシスタントです。\n"
                "以下のルールに従って、音声認識の出力を読みやすいプレーンテキストに整形してください：\n\n"
                "1. 句読点を適切に追加する\n"
                "2. 文の区切りを明確にする\n"
                "3. 明らかな認識ミスや不自然な繰り返しを修正する\n"
                "4. 「えー」「あー」などのフィラーワードを削除する\n"
                "5. 段落を適切に分ける（空行で区切る）\n"
                "6. 内容は変更せず、読みやすさのみを改善する\n\n"
                "【重要】出力形式の注意：\n"
                "- マークダウン記法（#、*、**、-、```など）は一切使用しないでください\n"
                "- 見出しや箇条書きは使用せず、通常の文章として出力してください\n"
                "- 装飾なしのプレーンテキストのみを出力してください"
            ),
        },
        {
            "role": "user",
            "content": f"以下の文字起こしテキストをプレーンテキストで整形してください：\n\n{raw_text}",
        },
    ]

    try:
        formatted = await call_llm(messages)
        return formatted.strip()
    except Exception as e:
        logger.error(f"LLM formatting failed: {e}")
        # Return raw text if LLM fails
        return raw_text


async def process_transcription(transcription_id: UUID, db_url: str):
    """
    Process a transcription request in the background.

    This function:
    1. Downloads audio from YouTube
    2. Transcribes audio using Whisper
    3. Formats text using LLM
    4. Updates database with results

    Args:
        transcription_id: UUID of the transcription record
        db_url: Database connection URL
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    # Create a new session for background task
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    audio_path = None

    try:
        # Get transcription record
        transcription = (
            db.query(Transcription).filter(Transcription.id == transcription_id).first()
        )

        if not transcription:
            logger.error(f"Transcription not found: {transcription_id}")
            return

        # Update status to processing
        transcription.processing_status = "processing"
        db.commit()

        logger.info(f"Processing transcription: {transcription_id}")

        # Step 1: Download audio
        audio_path, video_info = await download_youtube_audio(
            transcription.youtube_url,
            transcription.video_id,
        )

        # Update video title
        transcription.video_title = video_info.get("title")
        db.commit()

        # Step 2: Transcribe audio
        raw_text = await transcribe_audio(audio_path)
        transcription.raw_transcript = raw_text
        db.commit()

        # Step 3: Format with LLM
        formatted_text = await format_transcript_with_llm(raw_text)
        transcription.formatted_transcript = formatted_text

        # Mark as completed
        transcription.processing_status = "completed"
        db.commit()

        logger.info(f"Transcription completed: {transcription_id}")

    except Exception as e:
        logger.error(f"Transcription failed for {transcription_id}: {e}")
        try:
            transcription = (
                db.query(Transcription)
                .filter(Transcription.id == transcription_id)
                .first()
            )
            if transcription:
                transcription.processing_status = "failed"
                transcription.processing_error = str(e)
                db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update error status: {db_error}")

    finally:
        # Clean up audio file
        if audio_path and os.path.exists(audio_path):
            try:
                os.unlink(audio_path)
                logger.debug(f"Cleaned up audio file: {audio_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up audio file: {e}")

        db.close()


def start_transcription_background(transcription_id: UUID, db_url: str):
    """
    Start transcription processing in a background task.

    This function creates a new event loop for the background task
    to avoid issues with the main FastAPI event loop.

    Args:
        transcription_id: UUID of the transcription record
        db_url: Database connection URL
    """
    import threading

    def run_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(process_transcription(transcription_id, db_url))
        finally:
            loop.close()

    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()
    logger.info(f"Started background transcription task: {transcription_id}")
