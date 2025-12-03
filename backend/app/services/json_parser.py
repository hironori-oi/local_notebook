"""
JSON Parser utility for parsing LLM output as structured JSON.

This module provides robust parsing of LLM responses that may contain
JSON data with common formatting issues like markdown code blocks,
trailing commas, etc.
"""
import json
import re
import logging
from typing import TypeVar, Type

from pydantic import BaseModel, ValidationError
from app.core.exceptions import BadRequestError

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


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
        return schema.model_validate(data)
    except json.JSONDecodeError as e:
        errors.append(f"Direct parse failed: {e}")
    except ValidationError as e:
        errors.append(f"Validation failed: {e}")

    # Strategy 2: Extract from ```json ... ``` code block
    json_block_match = re.search(r'```json\s*([\s\S]*?)\s*```', response, re.IGNORECASE)
    if json_block_match:
        try:
            data = json.loads(json_block_match.group(1))
            return schema.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            errors.append(f"JSON code block parse failed: {e}")

    # Strategy 3: Extract from generic ``` ... ``` code block
    generic_block_match = re.search(r'```\s*([\s\S]*?)\s*```', response)
    if generic_block_match:
        try:
            data = json.loads(generic_block_match.group(1))
            return schema.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            errors.append(f"Generic code block parse failed: {e}")

    # Strategy 4: Find JSON object in the response
    # Look for content between first { and last }
    json_object_match = re.search(r'\{[\s\S]*\}', response)
    if json_object_match:
        json_str = json_object_match.group(0)

        # Try direct parse of extracted object
        try:
            data = json.loads(json_str)
            return schema.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as e:
            errors.append(f"Extracted object parse failed: {e}")

        # Try cleaning common issues
        cleaned = _clean_json_string(json_str)
        try:
            data = json.loads(cleaned)
            return schema.model_validate(data)
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
    cleaned = re.sub(r',\s*([}\]])', r'\1', json_str)

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
    json_block_match = re.search(r'```json\s*([\s\S]*?)\s*```', response, re.IGNORECASE)
    if json_block_match:
        return json_block_match.group(1).strip()

    # Try generic code block
    generic_block_match = re.search(r'```\s*([\s\S]*?)\s*```', response)
    if generic_block_match:
        content = generic_block_match.group(1).strip()
        # Verify it looks like JSON
        if content.startswith('{') or content.startswith('['):
            return content

    # Try to find JSON object directly
    json_object_match = re.search(r'\{[\s\S]*\}', response)
    if json_object_match:
        return json_object_match.group(0)

    raise BadRequestError("レスポンスからJSONを抽出できませんでした")
