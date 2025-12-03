"""
Janus-Pro-7B Image Generation Client

Client for generating images using the Janus-Pro-7B server API.
"""
import base64
import logging
from pathlib import Path
from typing import Optional, List, Tuple

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Directory for storing generated images
IMAGE_BASE_DIR = Path(settings.GENERATED_FILES_DIR) / "images"


async def generate_image(
    prompt: str,
    output_filename: str,
    width: Optional[int] = None,
    height: Optional[int] = None,
    cfg_weight: Optional[float] = None,
    temperature: Optional[float] = None,
    seed: Optional[int] = None,
) -> Optional[str]:
    """
    Generate an image using Janus-Pro-7B server and save it to file.

    Args:
        prompt: English text prompt for image generation
        output_filename: Filename to save the image (without extension)
        width: Image width in pixels (default from settings, 384 for Janus)
        height: Image height in pixels (default from settings, 384 for Janus)
        cfg_weight: Classifier-free guidance weight (default from settings)
        temperature: Sampling temperature (default from settings)
        seed: Random seed for reproducibility

    Returns:
        URL path to the generated image (/api/v1/assets/images/{filename}),
        or None if generation fails or is disabled
    """
    if not settings.JANUS_ENABLED:
        logger.info("Janus image generation is disabled, skipping")
        return None

    # Use defaults from settings if not specified
    if width is None:
        width = settings.JANUS_INFOGRAPHIC_WIDTH
    if height is None:
        height = settings.JANUS_INFOGRAPHIC_HEIGHT
    if cfg_weight is None:
        cfg_weight = settings.JANUS_CFG_WEIGHT
    if temperature is None:
        temperature = settings.JANUS_TEMPERATURE

    try:
        async with httpx.AsyncClient(timeout=settings.JANUS_TIMEOUT) as client:
            logger.info(f"Generating image via Janus server for prompt: {prompt[:100]}...")

            # Build the request payload for Janus server
            request_payload = {
                "prompt": prompt,
                "width": width,
                "height": height,
                "cfg_weight": cfg_weight,
                "temperature": temperature,
            }

            # Add seed if specified
            if seed is not None:
                request_payload["seed"] = seed

            response = await client.post(
                f"{settings.JANUS_API_BASE}/generate",
                json=request_payload,
            )
            response.raise_for_status()
            data = response.json()

            # Extract image from response
            if "images" not in data or not data["images"]:
                logger.warning("No images in Janus server response")
                return None

            # First image is the generated one
            img_base64 = data["images"][0]
            img_bytes = base64.b64decode(img_base64)

            # Ensure directory exists
            IMAGE_BASE_DIR.mkdir(parents=True, exist_ok=True)

            # Save image file
            filename = f"{output_filename}.png"
            file_path = IMAGE_BASE_DIR / filename
            file_path.write_bytes(img_bytes)

            logger.info(f"Generated image saved: {file_path}")
            return f"/api/v1/assets/images/{filename}"

    except httpx.ConnectError as e:
        logger.error(f"Failed to connect to Janus server at {settings.JANUS_API_BASE}: {e}")
        return None
    except httpx.TimeoutException as e:
        logger.error(f"Janus image generation timed out after {settings.JANUS_TIMEOUT}s: {e}")
        return None
    except httpx.HTTPStatusError as e:
        logger.error(f"Janus server returned error: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"Failed to generate image: {e}", exc_info=True)
        return None


async def generate_infographic_image(
    prompt: str,
    output_filename: str,
    seed: int = -1,
) -> Optional[str]:
    """
    Generate an image for infographic with infographic-specific dimensions.
    """
    return await generate_image(
        prompt=prompt,
        output_filename=output_filename,
        width=settings.JANUS_INFOGRAPHIC_WIDTH,
        height=settings.JANUS_INFOGRAPHIC_HEIGHT,
        seed=seed if seed >= 0 else None,
    )


async def generate_slide_image(
    prompt: str,
    output_filename: str,
    seed: int = -1,
) -> Optional[str]:
    """
    Generate an image for slides with slide-specific dimensions.
    """
    return await generate_image(
        prompt=prompt,
        output_filename=output_filename,
        width=settings.JANUS_SLIDE_WIDTH,
        height=settings.JANUS_SLIDE_HEIGHT,
        seed=seed if seed >= 0 else None,
    )


async def generate_images_batch(
    prompts: List[Tuple[str, str]],
    width: Optional[int] = None,
    height: Optional[int] = None,
    cfg_weight: Optional[float] = None,
    temperature: Optional[float] = None,
) -> dict[str, Optional[str]]:
    """
    Generate multiple images sequentially.

    Args:
        prompts: List of (prompt, filename) tuples
        width: Image width in pixels
        height: Image height in pixels
        cfg_weight: CFG weight
        temperature: Sampling temperature

    Returns:
        Dictionary mapping filename to image URL (or None if failed)
    """
    results = {}

    for idx, (prompt, filename) in enumerate(prompts):
        logger.info(f"Generating image {idx + 1}/{len(prompts)}: {filename}")
        url = await generate_image(
            prompt=prompt,
            output_filename=filename,
            width=width,
            height=height,
            cfg_weight=cfg_weight,
            temperature=temperature,
            seed=idx,
        )
        results[filename] = url

    return results


async def check_janus_health() -> dict:
    """
    Check if Janus server is reachable and responsive.

    Returns:
        Dict with 'status' and optional 'error' keys
    """
    if not settings.JANUS_ENABLED:
        return {"status": "disabled"}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{settings.JANUS_API_BASE}/health")
            response.raise_for_status()
            data = response.json()

            return {
                "status": "healthy",
                "api_base": settings.JANUS_API_BASE,
                "model": data.get("model", "unknown"),
                "device": data.get("device", "unknown"),
            }

    except httpx.ConnectError as e:
        return {
            "status": "unreachable",
            "api_base": settings.JANUS_API_BASE,
            "error": str(e),
        }
    except Exception as e:
        return {
            "status": "error",
            "api_base": settings.JANUS_API_BASE,
            "error": str(e),
        }
