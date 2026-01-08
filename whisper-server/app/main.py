"""
Whisper Server - Speech-to-Text API using faster-whisper.

This server provides a REST API endpoint for transcribing audio files
using the faster-whisper library with GPU acceleration support.
"""

import os
import tempfile
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from faster_whisper import WhisperModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from environment variables
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "large-v3")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cuda")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "float16")

app = FastAPI(
    title="Whisper Server",
    description="Speech-to-Text API using faster-whisper",
    version="1.0.0",
)

# Global model instance (loaded on startup)
model: Optional[WhisperModel] = None


@app.on_event("startup")
async def load_model():
    """Load Whisper model on server startup."""
    global model
    logger.info(f"Loading Whisper model: {WHISPER_MODEL}")
    logger.info(f"Device: {WHISPER_DEVICE}, Compute type: {WHISPER_COMPUTE_TYPE}")

    try:
        model = WhisperModel(
            WHISPER_MODEL,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
        )
        logger.info("Whisper model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load Whisper model: {e}")
        raise


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "model": WHISPER_MODEL,
        "device": WHISPER_DEVICE,
        "model_loaded": model is not None,
    }


@app.post("/transcribe")
async def transcribe(
    file: UploadFile = File(..., description="Audio file to transcribe"),
    language: str = Form(default="ja", description="Language code (e.g., 'ja', 'en')"),
):
    """
    Transcribe an audio file to text.

    Args:
        file: Audio file (MP3, WAV, M4A, etc.)
        language: Language code for transcription (default: 'ja')

    Returns:
        JSON with transcribed text
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Whisper model not loaded")

    # Validate file type
    allowed_extensions = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm"}
    file_ext = Path(file.filename).suffix.lower() if file.filename else ""
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Allowed: {allowed_extensions}",
        )

    # Save uploaded file to temporary location
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            temp_path = temp_file.name
            content = await file.read()
            temp_file.write(content)

        logger.info(f"Transcribing file: {file.filename} (language: {language})")

        # Perform transcription
        segments, info = model.transcribe(
            temp_path,
            language=language,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=500,
            ),
        )

        # Collect all segments into a single text
        texts = []
        for segment in segments:
            texts.append(segment.text.strip())

        full_text = "".join(texts)

        logger.info(
            f"Transcription completed. Duration: {info.duration:.2f}s, "
            f"Language: {info.language} ({info.language_probability:.2%})"
        )

        return JSONResponse(
            content={
                "text": full_text,
                "language": info.language,
                "language_probability": info.language_probability,
                "duration": info.duration,
            }
        )

    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

    finally:
        # Clean up temporary file
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Whisper Server",
        "version": "1.0.0",
        "model": WHISPER_MODEL,
        "endpoints": {
            "health": "/health",
            "transcribe": "/transcribe (POST)",
        },
    }
