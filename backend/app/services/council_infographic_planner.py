"""
Council Infographic Planner service for generating infographic structures using LLM.

This module handles the generation of structured JSON infographic content
from council meeting agendas using RAG context and LLM.
"""

import logging
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError
from app.models.llm_settings import LLMSettings
from app.schemas.infographic import InfographicStructure
from app.services.context_retriever import (
    format_context_for_prompt,
    retrieve_council_context,
)
from app.services.infographic_base import (
    build_system_prompt,
    build_user_template,
    generate_infographic_from_context,
)

logger = logging.getLogger(__name__)


# Additional rules specific to council infographics
COUNCIL_ADDITIONAL_RULES = (
    "- 発言者の意見や議論のポイントがあれば、誰がどのような意見を述べたかを含める"
)

# System prompt for council infographic generation (using shared base with additional rules)
COUNCIL_INFOGRAPHIC_SYSTEM_PROMPT = build_system_prompt(
    domain="審議会資料・議事録",
    additional_rules=COUNCIL_ADDITIONAL_RULES,
)

# User template for council infographic generation
COUNCIL_INFOGRAPHIC_USER_TEMPLATE = build_user_template(
    source_description="審議会の資料・議事録",
    footer_note="出典：審議会資料・議事録より作成",
)


def get_council_infographic_prompts(db: Session) -> Tuple[Optional[str], Optional[str]]:
    """
    Get custom council infographic prompts from LLM settings.

    Args:
        db: Database session

    Returns:
        Tuple of (system_prompt, user_template), both can be None if using defaults
    """
    # Get system-level LLM settings (user_id is NULL)
    settings_record = (
        db.query(LLMSettings).filter(LLMSettings.user_id.is_(None)).first()
    )

    if not settings_record or not settings_record.prompt_settings:
        return None, None

    prompt_settings = settings_record.prompt_settings
    system_prompt = prompt_settings.get("council_infographic_system")
    user_template = prompt_settings.get("council_infographic_user")

    return system_prompt, user_template


async def generate_council_infographic_structure(
    db: Session,
    meeting_id: UUID,
    topic: str,
    agenda_ids: Optional[List[UUID]],
    user_id: UUID,
) -> InfographicStructure:
    """
    Generate an infographic structure from council meeting agendas using LLM.

    Args:
        db: Database session
        meeting_id: Target council meeting UUID
        topic: Topic/prompt describing what the infographic should cover
        agenda_ids: Optional list of agenda UUIDs to use for context
        user_id: User ID for permission validation

    Returns:
        InfographicStructure with generated content

    Raises:
        BadRequestError: If context retrieval or JSON parsing fails
        LLMConnectionError: If LLM service is unavailable
    """
    logger.info(
        f"Generating council infographic for meeting {meeting_id}, topic: {topic[:50]}..."
    )

    # 1. Retrieve context from council agendas
    context_result = await retrieve_council_context(
        db=db,
        meeting_id=meeting_id,
        agenda_ids=agenda_ids,
        query=topic,
        user_id=user_id,
        top_k=10,  # Get more context for comprehensive infographic
    )

    if not context_result.contexts:
        raise BadRequestError(
            "インフォグラフィック生成に必要なコンテキストが見つかりませんでした。"
            "この開催回に処理済みの資料または議事録を追加してください。"
        )

    # 2. Format context for prompt
    context_text = format_context_for_prompt(context_result)

    # 3. Get custom prompts if available
    custom_system, custom_user = get_council_infographic_prompts(db)
    system_prompt = (
        custom_system if custom_system else COUNCIL_INFOGRAPHIC_SYSTEM_PROMPT
    )
    user_template = custom_user if custom_user else COUNCIL_INFOGRAPHIC_USER_TEMPLATE

    # 4. Generate using shared function
    return await generate_infographic_from_context(
        context_text=context_text,
        topic=topic,
        system_prompt=system_prompt,
        user_template=user_template,
        domain_name="council",
    )
