"""
Janus-Pro-7B Image Generation API Server

FastAPI server for text-to-image generation using DeepSeek Janus-Pro-7B.
"""
import logging
from contextlib import asynccontextmanager
from typing import Optional, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.config import settings
from app.generator import load_model, generate_image, image_to_base64

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model on startup."""
    logger.info("Starting Janus-Pro-7B Image Generation Server...")
    load_model()
    logger.info("Server ready!")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Janus-Pro-7B Image Generation API",
    description="Text-to-image generation using DeepSeek Janus-Pro-7B",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class GenerateRequest(BaseModel):
    """Request model for image generation."""

    prompt: str = Field(..., description="Text prompt for image generation")
    width: int = Field(default=384, description="Image width (384 recommended)")
    height: int = Field(default=384, description="Image height (384 recommended)")
    cfg_weight: float = Field(default=5.0, description="CFG guidance weight")
    temperature: float = Field(default=1.0, description="Sampling temperature")
    top_p: float = Field(default=1.0, description="Top-p sampling")
    seed: Optional[int] = Field(default=None, description="Random seed")

    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "A beautiful sunset over mountains, digital art style",
                "width": 384,
                "height": 384,
                "cfg_weight": 5.0,
                "temperature": 1.0,
            }
        }


class GenerateResponse(BaseModel):
    """Response model for image generation."""

    images: List[str] = Field(..., description="List of base64-encoded PNG images")
    width: int
    height: int


class BatchGenerateRequest(BaseModel):
    """Request model for batch image generation."""

    prompts: List[str] = Field(..., description="List of prompts")
    width: int = Field(default=384)
    height: int = Field(default=384)
    cfg_weight: float = Field(default=5.0)
    temperature: float = Field(default=1.0)


class BatchGenerateResponse(BaseModel):
    """Response model for batch image generation."""

    images: List[str] = Field(..., description="List of base64-encoded PNG images")
    count: int


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    model: str
    device: str


@app.get("/health", response_model=HealthResponse)
def health_check():
    """Check if the server is healthy and model is loaded."""
    return HealthResponse(
        status="healthy",
        model=settings.MODEL_NAME,
        device=settings.DEVICE,
    )


@app.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """
    Generate an image from a text prompt.

    Returns a base64-encoded PNG image.
    """
    try:
        logger.info(f"Received generation request: {request.prompt[:50]}...")

        image = await generate_image(
            prompt=request.prompt,
            width=request.width,
            height=request.height,
            cfg_weight=request.cfg_weight,
            temperature=request.temperature,
            top_p=request.top_p,
            seed=request.seed,
        )

        image_base64 = image_to_base64(image)

        logger.info("Image generated successfully")
        return GenerateResponse(
            images=[image_base64],
            width=request.width,
            height=request.height,
        )

    except Exception as e:
        logger.error(f"Generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate/batch", response_model=BatchGenerateResponse)
async def generate_batch(request: BatchGenerateRequest):
    """
    Generate multiple images from a list of prompts.

    Images are generated sequentially to avoid OOM errors.
    """
    try:
        logger.info(f"Received batch generation request: {len(request.prompts)} prompts")

        images_base64 = []
        for idx, prompt in enumerate(request.prompts):
            logger.info(f"Generating image {idx + 1}/{len(request.prompts)}")

            image = await generate_image(
                prompt=prompt,
                width=request.width,
                height=request.height,
                cfg_weight=request.cfg_weight,
                temperature=request.temperature,
                seed=idx,
            )
            images_base64.append(image_to_base64(image))

        logger.info(f"Batch generation complete: {len(images_base64)} images")
        return BatchGenerateResponse(
            images=images_base64,
            count=len(images_base64),
        )

    except Exception as e:
        logger.error(f"Batch generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,
    )
