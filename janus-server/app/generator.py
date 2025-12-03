"""
Janus-Pro-7B Image Generator

Based on DeepSeek's official Janus implementation for text-to-image generation.
https://github.com/deepseek-ai/Janus
"""
import logging
import asyncio
from typing import Optional, List
from io import BytesIO
import base64
from PIL import Image
import numpy as np

import torch

from app.config import settings

logger = logging.getLogger(__name__)

# Global model instances
_model = None
_processor = None
_tokenizer = None
_model_lock = asyncio.Lock()


def _get_torch_dtype():
    """Get torch dtype from settings."""
    if settings.TORCH_DTYPE == "bfloat16":
        return torch.bfloat16
    elif settings.TORCH_DTYPE == "float16":
        return torch.float16
    else:
        return torch.float32


def load_model():
    """
    Load Janus-Pro-7B model and processor.
    This should be called once at startup.
    """
    global _model, _processor, _tokenizer

    if _model is not None:
        logger.info("Model already loaded")
        return

    logger.info(f"Loading Janus model: {settings.MODEL_NAME}")

    try:
        from transformers import AutoModelForCausalLM
        from janus.models import VLChatProcessor

        # Load processor (includes tokenizer)
        _processor = VLChatProcessor.from_pretrained(settings.MODEL_NAME)
        _tokenizer = _processor.tokenizer
        logger.info("Processor loaded successfully")

        # Load model with trust_remote_code for Janus custom architecture
        _model = AutoModelForCausalLM.from_pretrained(
            settings.MODEL_NAME,
            torch_dtype=_get_torch_dtype(),
            trust_remote_code=True,
        )
        _model = _model.to(settings.DEVICE).eval()

        logger.info(f"Model loaded successfully on {settings.DEVICE}")

    except ImportError as e:
        logger.error(f"Failed to import required library: {e}")
        logger.error("Please install: pip install janus-model transformers")
        raise
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise


def get_model():
    """Get the loaded model instance."""
    if _model is None:
        raise RuntimeError("Model not loaded. Call load_model() first.")
    return _model


def get_processor():
    """Get the loaded processor instance."""
    if _processor is None:
        raise RuntimeError("Processor not loaded. Call load_model() first.")
    return _processor


def get_tokenizer():
    """Get the loaded tokenizer instance."""
    if _tokenizer is None:
        raise RuntimeError("Tokenizer not loaded. Call load_model() first.")
    return _tokenizer


@torch.inference_mode()
def generate_image_sync(
    prompt: str,
    width: int = 384,
    height: int = 384,
    cfg_weight: float = 5.0,
    temperature: float = 1.0,
    top_p: float = 1.0,
    seed: Optional[int] = None,
) -> Image.Image:
    """
    Generate an image from text prompt using Janus-Pro-7B.

    Uses the official generation method from Janus repository.

    Args:
        prompt: Text description of the image to generate
        width: Output image width (384 for Janus-Pro-7B)
        height: Output image height (384 for Janus-Pro-7B)
        cfg_weight: Classifier-free guidance weight (default: 5.0)
        temperature: Sampling temperature (default: 1.0)
        top_p: Top-p sampling parameter (default: 1.0)
        seed: Random seed for reproducibility

    Returns:
        PIL Image object
    """
    model = get_model()
    processor = get_processor()
    tokenizer = get_tokenizer()

    # Set seed if provided
    if seed is not None:
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)

    logger.info(f"Generating image for prompt: {prompt[:100]}...")

    # Janus text-to-image conversation format
    conversation = [
        {
            "role": "<|User|>",
            "content": prompt,
        },
        {"role": "<|Assistant|>", "content": ""},
    ]

    # Apply SFT template
    sft_format = processor.apply_sft_template_for_multi_turn_prompts(
        conversations=conversation,
        sft_format=processor.sft_format,
        system_prompt="",
    )

    # Add image generation start token
    full_prompt = sft_format + processor.image_start_tag

    # Tokenize
    input_ids = tokenizer.encode(full_prompt)
    input_ids = torch.LongTensor(input_ids).unsqueeze(0).to(settings.DEVICE)

    # Calculate number of image tokens
    # Janus uses 16x16 patches, so 384x384 = 24x24 = 576 tokens
    h_tokens = height // 16
    w_tokens = width // 16
    num_image_tokens = h_tokens * w_tokens

    logger.info(f"Generating {num_image_tokens} image tokens ({h_tokens}x{w_tokens})...")

    # Parallel CFG: duplicate input for conditional and unconditional
    parallel_size = 2
    input_ids = input_ids.repeat(parallel_size, 1)

    # Get input embeddings
    inputs_embeds = model.language_model.get_input_embeddings()(input_ids)

    # Initialize past_key_values
    past_key_values = None

    # Generate image tokens one by one
    generated_tokens = []

    for step in range(num_image_tokens):
        if step % 100 == 0:
            logger.info(f"  Step {step}/{num_image_tokens}")

        # Forward pass
        outputs = model.language_model.model(
            inputs_embeds=inputs_embeds,
            past_key_values=past_key_values,
            use_cache=True,
            return_dict=True,
        )
        past_key_values = outputs.past_key_values
        hidden_states = outputs.last_hidden_state[:, -1, :]

        # Get logits from generation head
        logits = model.gen_head(hidden_states)

        # Apply CFG
        logits_cond = logits[0:1]
        logits_uncond = logits[1:2]
        logits_cfg = logits_uncond + cfg_weight * (logits_cond - logits_uncond)

        # Sample token
        probs = torch.softmax(logits_cfg / temperature, dim=-1)

        # Apply top-p filtering
        if top_p < 1.0:
            sorted_probs, sorted_indices = torch.sort(probs, descending=True, dim=-1)
            cumsum_probs = torch.cumsum(sorted_probs, dim=-1)
            mask = cumsum_probs - sorted_probs > top_p
            sorted_probs[mask] = 0.0
            sorted_probs = sorted_probs / sorted_probs.sum(dim=-1, keepdim=True)
            probs = torch.zeros_like(probs).scatter_(1, sorted_indices, sorted_probs)

        next_token = torch.multinomial(probs, num_samples=1)
        generated_tokens.append(next_token.item())

        # Prepare embedding for next step
        # Expand token to parallel size for CFG
        next_token_expanded = next_token.expand(parallel_size, -1)
        next_embeds = model.prepare_gen_img_embeds(next_token_expanded)
        inputs_embeds = next_embeds

    logger.info("Decoding image tokens to pixels...")

    # Convert tokens to tensor
    gen_tokens = torch.LongTensor(generated_tokens).view(1, h_tokens, w_tokens).to(settings.DEVICE)

    # Decode tokens to image using the visual decoder
    # The gen_vision_model.decode_code expects specific shape
    decoded = model.gen_vision_model.decode_code(
        gen_tokens,
        shape=(1, 8, height // 8, width // 8),
    )

    # Post-process: normalize and convert to image
    decoded = decoded.float().cpu().numpy()
    decoded = np.clip((decoded + 1) / 2 * 255, 0, 255).astype(np.uint8)
    decoded = decoded.transpose(0, 2, 3, 1)  # BCHW -> BHWC

    image = Image.fromarray(decoded[0])

    logger.info(f"Image generated successfully: {image.size}")
    return image


async def generate_image(
    prompt: str,
    width: int = 384,
    height: int = 384,
    cfg_weight: float = 5.0,
    temperature: float = 1.0,
    top_p: float = 1.0,
    seed: Optional[int] = None,
) -> Image.Image:
    """
    Async wrapper for image generation.
    Uses a lock to prevent concurrent generation (GPU memory constraints).
    """
    async with _model_lock:
        loop = asyncio.get_event_loop()
        image = await loop.run_in_executor(
            None,
            lambda: generate_image_sync(
                prompt=prompt,
                width=width,
                height=height,
                cfg_weight=cfg_weight,
                temperature=temperature,
                top_p=top_p,
                seed=seed,
            ),
        )
        return image


def image_to_base64(image: Image.Image, format: str = "PNG") -> str:
    """Convert PIL Image to base64 string."""
    buffer = BytesIO()
    image.save(buffer, format=format)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


async def generate_images_batch(
    prompts: List[str],
    width: int = 384,
    height: int = 384,
    cfg_weight: float = 5.0,
    temperature: float = 1.0,
) -> List[Image.Image]:
    """Generate multiple images sequentially."""
    images = []
    for idx, prompt in enumerate(prompts):
        logger.info(f"Generating image {idx + 1}/{len(prompts)}")
        image = await generate_image(
            prompt=prompt,
            width=width,
            height=height,
            cfg_weight=cfg_weight,
            temperature=temperature,
            seed=idx,
        )
        images.append(image)
    return images
