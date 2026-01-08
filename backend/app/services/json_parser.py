"""
JSON Parser utility for parsing LLM output as structured JSON.

This module provides robust parsing of LLM responses that may contain
JSON data with common formatting issues like markdown code blocks,
trailing commas, etc.
"""

import json
import logging
import re
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError

from app.core.exceptions import BadRequestError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


# Mapping of Japanese key names to English for EmailContent schema
EMAIL_CONTENT_KEY_MAPPING = {
    # Top-level keys
    "要約": "document_summary",
    "資料の要約": "document_summary",
    "資料の概要": "document_summary",
    "document_summary": "document_summary",
    "発言者別意見": "speaker_opinions",
    "発言者別整理": "speaker_opinions",
    "議論の発言者別整理": "speaker_opinions",
    "speaker_opinions": "speaker_opinions",
    "補足": "additional_notes",
    "補足事項": "additional_notes",
    "additional_notes": "additional_notes",
    # Nested keys for speaker opinions
    "発言者": "speaker",
    "発言者名": "speaker",
    "speaker": "speaker",
    "意見": "opinions",
    "意見リスト": "opinions",
    "opinions": "opinions",
}


def _map_japanese_keys(data: dict) -> dict:
    """
    Map Japanese key names to English for EmailContent compatibility.

    Args:
        data: Dictionary with potentially Japanese keys

    Returns:
        Dictionary with English keys mapped
    """
    if not isinstance(data, dict):
        return data

    result = {}

    for key, value in data.items():
        # Map the key if it's in our mapping
        english_key = EMAIL_CONTENT_KEY_MAPPING.get(key, key)

        # Handle nested structures
        if english_key == "speaker_opinions":
            # Handle various formats of speaker opinions
            if isinstance(value, list):
                # Already a list format
                mapped_opinions = []
                for item in value:
                    if isinstance(item, dict):
                        mapped_item = {}
                        for k, v in item.items():
                            mapped_k = EMAIL_CONTENT_KEY_MAPPING.get(k, k)
                            mapped_item[mapped_k] = v
                        mapped_opinions.append(mapped_item)
                    else:
                        mapped_opinions.append(item)
                result[english_key] = mapped_opinions
            elif isinstance(value, dict):
                # Dictionary format (speaker name as key, opinions as value)
                # Convert to list format
                mapped_opinions = []
                for speaker_name, opinions in value.items():
                    if isinstance(opinions, list):
                        mapped_opinions.append(
                            {"speaker": speaker_name, "opinions": opinions}
                        )
                    elif isinstance(opinions, str):
                        mapped_opinions.append(
                            {"speaker": speaker_name, "opinions": [opinions]}
                        )
                result[english_key] = mapped_opinions
            else:
                result[english_key] = value
        elif english_key == "document_summary":
            # Handle case where summary might be in a nested structure
            if isinstance(value, dict):
                # Extract text from nested structure (like "要点" -> "資料の概要")
                summary_parts = []
                for nested_key, nested_value in value.items():
                    if isinstance(nested_value, list):
                        summary_parts.extend(nested_value)
                    elif isinstance(nested_value, str):
                        summary_parts.append(nested_value)
                result[english_key] = " ".join(summary_parts)
            else:
                result[english_key] = value
        else:
            result[english_key] = value

    return result


def parse_llm_json(response: str, schema: Type[T]) -> T:
    """
    Parse LLM response as JSON and validate against a Pydantic schema.

    This function attempts multiple parsing strategies to handle common
    LLM output formatting issues:
    1. Direct JSON parse
    2. Extract JSON from markdown code blocks (```json ... ```)
    3. Extract JSON from generic code blocks (``` ... ```)
    4. Clean trailing commas and other common issues

    Args:
        response: Raw LLM response string
        schema: Pydantic model class to validate against

    Returns:
        Validated Pydantic model instance

    Raises:
        BadRequestError: If JSON parsing or validation fails after all attempts
    """
    if not response or not response.strip():
        raise BadRequestError("LLM出力が空です")

    errors = []

    # Strategy 1: Direct JSON parse
    try:
        data = json.loads(response)
        logger.debug(
            f"Direct JSON parse successful. Keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}"
        )
        # Try with key mapping for EmailContent compatibility
        mapped_data = _map_japanese_keys(data) if isinstance(data, dict) else data
        return schema.model_validate(mapped_data)
    except json.JSONDecodeError as e:
        errors.append(f"Direct parse failed: {e}")
    except ValidationError as e:
        errors.append(f"Validation failed: {e}")
        logger.warning(f"JSON parsed but validation failed. Data: {data}")

    # Strategy 2: Extract from ```json ... ``` code block
    json_block_match = re.search(r"```json\s*([\s\S]*?)\s*```", response, re.IGNORECASE)
    if json_block_match:
        try:
            data = json.loads(json_block_match.group(1))
            mapped_data = _map_japanese_keys(data) if isinstance(data, dict) else data
            return schema.model_validate(mapped_data)
        except (json.JSONDecodeError, ValidationError) as e:
            errors.append(f"JSON code block parse failed: {e}")

    # Strategy 3: Extract from generic ``` ... ``` code block
    generic_block_match = re.search(r"```\s*([\s\S]*?)\s*```", response)
    if generic_block_match:
        try:
            data = json.loads(generic_block_match.group(1))
            mapped_data = _map_japanese_keys(data) if isinstance(data, dict) else data
            return schema.model_validate(mapped_data)
        except (json.JSONDecodeError, ValidationError) as e:
            errors.append(f"Generic code block parse failed: {e}")

    # Strategy 4: Find JSON object in the response
    # Look for content between first { and last }
    json_object_match = re.search(r"\{[\s\S]*\}", response)
    if json_object_match:
        json_str = json_object_match.group(0)

        # Try direct parse of extracted object
        try:
            data = json.loads(json_str)
            mapped_data = _map_japanese_keys(data) if isinstance(data, dict) else data
            return schema.model_validate(mapped_data)
        except (json.JSONDecodeError, ValidationError) as e:
            errors.append(f"Extracted object parse failed: {e}")

        # Try cleaning common issues
        cleaned = _clean_json_string(json_str)
        try:
            data = json.loads(cleaned)
            mapped_data = _map_japanese_keys(data) if isinstance(data, dict) else data
            return schema.model_validate(mapped_data)
        except (json.JSONDecodeError, ValidationError) as e:
            errors.append(f"Cleaned JSON parse failed: {e}")

    # All strategies failed
    logger.error(f"JSON parsing failed after all strategies. Errors: {errors}")
    logger.debug(f"Original response (first 500 chars): {response[:500]}")

    raise BadRequestError(
        f"LLM出力のJSON解析に失敗しました。出力形式が正しくない可能性があります。"
    )


def _clean_json_string(json_str: str) -> str:
    """
    Clean common JSON formatting issues from LLM output.

    Args:
        json_str: Raw JSON string to clean

    Returns:
        Cleaned JSON string
    """
    # Remove trailing commas before ] or }
    cleaned = re.sub(r",\s*([}\]])", r"\1", json_str)

    # Remove any leading/trailing whitespace
    cleaned = cleaned.strip()

    # Fix single quotes (some LLMs use single quotes)
    # Be careful not to break strings containing apostrophes
    # This is a simple heuristic that may not work in all cases
    if "'" in cleaned and '"' not in cleaned:
        cleaned = cleaned.replace("'", '"')

    return cleaned


def extract_json_from_response(response: str) -> str:
    """
    Extract the JSON portion from an LLM response.

    This is useful when you want to get the raw JSON string
    without parsing it into a Pydantic model.

    Args:
        response: Raw LLM response string

    Returns:
        Extracted JSON string

    Raises:
        BadRequestError: If no JSON found in response
    """
    # Try markdown code block first
    json_block_match = re.search(r"```json\s*([\s\S]*?)\s*```", response, re.IGNORECASE)
    if json_block_match:
        return json_block_match.group(1).strip()

    # Try generic code block
    generic_block_match = re.search(r"```\s*([\s\S]*?)\s*```", response)
    if generic_block_match:
        content = generic_block_match.group(1).strip()
        # Verify it looks like JSON
        if content.startswith("{") or content.startswith("["):
            return content

    # Try to find JSON object directly
    json_object_match = re.search(r"\{[\s\S]*\}", response)
    if json_object_match:
        return json_object_match.group(0)

    raise BadRequestError("レスポンスからJSONを抽出できませんでした")
