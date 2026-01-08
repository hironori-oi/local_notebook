"""
Infographic Planner service for generating infographic structures using LLM.

This module handles the generation of structured JSON infographic content
from notebook sources using RAG context and LLM.
"""
import logging
import json
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.schemas.infographic import InfographicStructure
from app.services.context_retriever import retrieve_context, format_context_for_prompt
from app.services.infographic_base import (
    build_system_prompt,
    build_user_template,
    generate_infographic_from_context,
)
from app.core.exceptions import BadRequestError
from app.models.llm_settings import LLMSettings

logger = logging.getLogger(__name__)


# System prompt for infographic generation (using shared base)
INFOGRAPHIC_SYSTEM_PROMPT = build_system_prompt(domain="社内資料")

# User template for notebook infographic generation
INFOGRAPHIC_USER_TEMPLATE = build_user_template(
    source_description="社内資料",
    footer_note="出典や補足情報",
)


def get_infographic_prompts(db: Session) -> Tuple[Optional[str], Optional[str]]:
    """
    Get custom infographic prompts from LLM settings.

    Args:
        db: Database session

    Returns:
        Tuple of (system_prompt, user_template), both can be None if using defaults
    """
    # Get system-level LLM settings (user_id is NULL)
    settings_record = db.query(LLMSettings).filter(LLMSettings.user_id.is_(None)).first()

    if not settings_record or not settings_record.prompt_settings:
        return None, None

    prompt_settings = settings_record.prompt_settings
    system_prompt = prompt_settings.get("infographic_system")
    user_template = prompt_settings.get("infographic_user")

    return system_prompt, user_template


async def generate_infographic_structure(
    db: Session,
    notebook_id: UUID,
    topic: str,
    source_ids: Optional[List[UUID]],
    user_id: UUID,
) -> InfographicStructure:
    """
    Generate an infographic structure from notebook sources using LLM.

    Args:
        db: Database session
        notebook_id: Target notebook UUID
        topic: Topic/prompt describing what the infographic should cover
        source_ids: Optional list of source UUIDs to use for context
        user_id: User ID for permission validation

    Returns:
        InfographicStructure with generated content

    Raises:
        BadRequestError: If context retrieval or JSON parsing fails
        LLMConnectionError: If LLM service is unavailable
    """
    logger.info(f"Generating infographic for notebook {notebook_id}, topic: {topic[:50]}...")

    # 1. Retrieve context from sources
    context_result = await retrieve_context(
        db=db,
        notebook_id=notebook_id,
        source_ids=source_ids,
        query=topic,
        user_id=user_id,
        top_k=10,  # Get more context for comprehensive infographic
    )

    if not context_result.contexts:
        raise BadRequestError(
            "インフォグラフィック生成に必要なコンテキストが見つかりませんでした。"
            "ノートブックにソースを追加してください。"
        )

    # 2. Format context for prompt
    context_text = format_context_for_prompt(context_result)

    # 3. Get custom prompts if available
    custom_system, custom_user = get_infographic_prompts(db)
    system_prompt = custom_system if custom_system else INFOGRAPHIC_SYSTEM_PROMPT
    user_template = custom_user if custom_user else INFOGRAPHIC_USER_TEMPLATE

    # 4. Generate using shared function
    return await generate_infographic_from_context(
        context_text=context_text,
        topic=topic,
        system_prompt=system_prompt,
        user_template=user_template,
        domain_name="notebook",
    )


def get_infographic_schema_example() -> str:
    """
    Get an example JSON schema for infographic generation.

    Returns:
        JSON string with example schema
    """
    example = {
        "title": "再エネ導入拡大のポイント",
        "subtitle": "需給調整と系統安定化の観点から",
        "sections": [
            {
                "id": "section_1",
                "heading": "現状の課題：需給バランスの変動拡大",
                "icon_hint": "warning",
                "color_hint": "warning",
                "key_points": [
                    "再エネ比率の拡大に伴い、天候による発電量の変動が大きくなり、電力の需給バランスを保つことが難しくなっている",
                    "特に太陽光発電は日中の出力変動が激しく、急激な出力低下時に他の電源でカバーする必要がある",
                    "従来の火力発電は起動・停止に時間がかかるため、短時間の変動への対応が困難になっている",
                    "一部のエリアでは再エネの発電量が需要を上回り、出力制御（発電の抑制）を行うケースが増加している"
                ],
                "detail": "再エネ導入拡大に伴い、特に太陽光発電の出力変動への対応が急務となっている。従来の火力発電による調整では応答速度に限界があり、新たな調整力の確保が必要。電力システム全体での対応策が求められている。",
                "image_prompt_en": "flat infographic style, warning icon, fluctuating line graph showing energy supply demand imbalance, orange and yellow colors with red accent, minimal clean design"
            },
            {
                "id": "section_2",
                "heading": "必要となる調整力の種類",
                "icon_hint": "chart",
                "color_hint": "primary",
                "key_points": [
                    "短周期調整力は数分〜十数分単位の変動に対応するもので、蓄電池や揚水発電など応答速度の速い設備が適している",
                    "長周期調整力は数時間単位の変動に対応するもので、LNG火力など起動時間は長いが持続的に出力調整できる電源が担う",
                    "デマンドレスポンス（DR）は需要側で電力使用を調整する仕組みで、工場の操業シフトなどにより需給バランスを改善できる",
                    "地域間連系線を活用することで、余剰電力を他エリアに送電し、エリア間で需給を融通し合うことが可能になる"
                ],
                "detail": "調整力は応答速度によって短周期・長周期に分類され、それぞれ異なる電源・設備で対応する。単一の手段ではなく、複数の調整力を組み合わせて電力システム全体の安定性を確保することが重要。",
                "image_prompt_en": "flat infographic style, comparison diagram showing battery vs thermal power response time, blue and green colors with icons, professional business chart, clean white background"
            },
            {
                "id": "section_3",
                "heading": "主な対策と取り組み",
                "icon_hint": "lightbulb",
                "color_hint": "accent",
                "key_points": [
                    "系統用蓄電池の導入により、短時間の需給変動に素早く対応できる調整力を確保し、再エネの出力制御を減らすことを目指す",
                    "既存の火力発電所に柔軟性向上のための改修を行い、より速い起動・出力調整ができるよう設備を改善する",
                    "DR普及のためのインセンティブ制度を整備し、需要家が電力使用を調整するメリットを提供することで参加を促進する",
                    "連系線の増強工事を進め、エリア間での電力融通能力を高めることで、局所的な需給アンバランスを解消する"
                ],
                "detail": "各対策はそれぞれ特徴があり、蓄電池は即応性、火力改修は既存資産活用、DRは需要側参加、連系線は広域対応という役割を担う。これらを総合的に推進することで、再エネ大量導入時代の電力システムを支える。",
                "image_prompt_en": "flat infographic style, four solution icons battery storage DR transmission grid, purple and blue accent colors, clean minimalist design, professional presentation"
            },
            {
                "id": "section_4",
                "heading": "今後のアクションと推進体制",
                "icon_hint": "target",
                "color_hint": "success",
                "key_points": [
                    "系統用蓄電池の入札公募を実施し、事業者を選定して導入を進める。設置場所は系統の状況を踏まえて決定する",
                    "DR事業者との契約締結を進め、需要側の調整力を確保する。参加のハードルを下げる制度設計も並行して検討する",
                    "連系線増強工事に着手し、計画的に工事を進める。工事期間中の系統運用への影響も考慮しながら実施する",
                    "進捗状況を定期的にモニタリングし、目標達成状況を評価する。必要に応じて計画の見直しや追加対策を検討する"
                ],
                "detail": "各施策を並行して進め、必要な調整力を段階的に確保していく。関係部門・事業者との連携体制を構築し、進捗管理と課題解決を継続的に行う。状況変化に応じて柔軟に計画を見直すことも重要。",
                "image_prompt_en": "flat infographic style, timeline roadmap with action items and milestones, checkmark icons, green progress indicators, clean minimalist design, professional business presentation"
            }
        ],
        "footer_note": "出典：社内資料より作成"
    }
    return json.dumps(example, ensure_ascii=False, indent=2)
