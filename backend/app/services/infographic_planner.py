"""
Infographic Planner service for generating infographic structures using LLM.

This module handles the generation of structured JSON infographic content
from notebook sources using RAG context and LLM.
"""
import logging
import json
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.schemas.infographic import InfographicStructure
from app.services.context_retriever import retrieve_context, format_context_for_prompt
from app.services.llm_client import call_generation_llm
from app.services.json_parser import parse_llm_json
from app.core.exceptions import BadRequestError, LLMConnectionError

logger = logging.getLogger(__name__)


# System prompt for infographic generation
INFOGRAPHIC_SYSTEM_PROMPT = """あなたは社内資料の構成を専門的に設計する情報アーキテクト兼デザイナーです。

【重要】いきなりJSONを生成せず、以下のステップで深く考えてください：

1. まず資料全体の論点・ストーリーラインを整理する
2. 「1枚のインフォグラフィックとして最も伝わりやすい構成」を決める
3. 各セクションに適切なビジュアル（図解）を計画する
4. 最後に構成要素をJSONで出力する

## 出力ルール
1. 必ず有効なJSONのみを出力してください。説明文やマークダウンは不要です。
2. セクションは3〜6個を目安にしてください。
3. 各セクションには見出し、アイコンヒント、2〜4個のキーポイントを含めてください。
4. 日本語テキスト出力。ただし image_prompt_en は必ず英語で記述してください。
5. 各セクションに image_prompt_en を必ず含めてください（画像生成用の英語プロンプト）。

## image_prompt_en の書き方
- 英語で記述
- フラットなインフォグラフィックスタイルを指定
- 具体的な視覚要素を含める
- 例: "flat infographic style, minimal design, pie chart showing 60% renewable energy, green and blue colors, clean white background, professional business presentation"

## icon_hint で使用可能な値
- lightbulb（アイデア・ポイント）
- chart（データ・統計）
- target（目標・ゴール）
- users（人・チーム）
- shield（安全・セキュリティ）
- clock（時間・スケジュール）
- warning（注意・リスク）
- check（完了・確認）
- arrow（プロセス・流れ）
- star（重要・おすすめ）

## color_hint で使用可能な値
- primary（メイン色・青系）
- secondary（サブ色・グレー系）
- accent（アクセント色・紫系）
- success（成功・緑系）
- warning（警告・黄色系）
- danger（危険・赤系）
"""

INFOGRAPHIC_USER_TEMPLATE = """以下は社内資料から抽出した関連部分です：

---
{context}
---

この内容をもとに、以下のトピックに関する1ページのインフォグラフィック構造を生成してください。

【トピック】
{topic}

【出力JSONスキーマ】
{{
  "title": "インフォグラフィックのタイトル",
  "subtitle": "サブタイトル（省略可）",
  "sections": [
    {{
      "id": "section_1",
      "heading": "セクション見出し",
      "icon_hint": "lightbulb",
      "color_hint": "primary",
      "key_points": ["ポイント1", "ポイント2", "ポイント3"],
      "detail": "詳細説明（省略可）",
      "image_prompt_en": "flat infographic style, minimal design, lightbulb icon with innovation concept, blue and white colors, clean background"
    }}
  ],
  "footer_note": "フッターノート（省略可）"
}}

【重要】
- 各セクションに image_prompt_en を必ず含めてください
- image_prompt_en は英語で、フラットなインフォグラフィックスタイルを指定

JSONのみを出力してください："""


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

    # 3. Build LLM messages
    user_content = INFOGRAPHIC_USER_TEMPLATE.format(
        context=context_text,
        topic=topic,
    )

    messages = [
        {"role": "system", "content": INFOGRAPHIC_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    # 4. Call LLM
    try:
        raw_response = await call_generation_llm(messages, temperature=0.3)
    except Exception as e:
        logger.error(f"LLM call failed for infographic generation: {e}")
        raise LLMConnectionError(f"LLMサービスへの接続に失敗しました: {str(e)}")

    # 5. Parse and validate JSON response
    structure = parse_llm_json(raw_response, InfographicStructure)

    # 6. Post-process: ensure all sections have IDs
    for i, section in enumerate(structure.sections):
        if not section.id:
            section.id = f"section_{i + 1}"

    # 7. Generate images for each section using Janus
    structure = await _generate_images_for_structure(structure, notebook_id)

    logger.info(f"Successfully generated infographic with {len(structure.sections)} sections")
    return structure


async def _generate_images_for_structure(
    structure: InfographicStructure,
    notebook_id: UUID,
) -> InfographicStructure:
    """
    Generate images for each section in the infographic structure.

    Args:
        structure: The infographic structure with image prompts
        notebook_id: Notebook ID for unique filename generation

    Returns:
        Updated structure with image URLs
    """
    from app.services.image_client import generate_infographic_image

    for idx, section in enumerate(structure.sections):
        if section.image_prompt_en:
            # Generate unique filename
            filename = f"infographic_{notebook_id}_{section.id}"

            logger.info(f"Generating image for section {section.id}: {section.image_prompt_en[:50]}...")

            image_url = await generate_infographic_image(
                prompt=section.image_prompt_en,
                output_filename=filename,
                seed=idx,
            )

            if image_url:
                section.image_url = image_url
                logger.info(f"Generated image for section {section.id}: {image_url}")
            else:
                logger.warning(f"Failed to generate image for section {section.id}")

    return structure


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
                "heading": "現状の課題",
                "icon_hint": "warning",
                "color_hint": "warning",
                "key_points": [
                    "再エネ比率の拡大に伴い、需給バランスの変動が大きくなっている",
                    "太陽光の出力変動が日中の調整力を圧迫",
                    "既存の火力発電では対応が困難な場面も"
                ],
                "detail": None,
                "image_prompt_en": "flat infographic style, warning icon, fluctuating graph showing energy supply and demand imbalance, orange and white colors, minimal clean design"
            },
            {
                "id": "section_2",
                "heading": "必要となる調整力",
                "icon_hint": "chart",
                "color_hint": "primary",
                "key_points": [
                    "短周期・長周期それぞれの調整力確保が必要",
                    "火力・蓄電池・DRの組み合わせ",
                    "地域間連系線の活用"
                ],
                "detail": "調整力の種類と確保方法について詳細に検討が必要",
                "image_prompt_en": "flat infographic style, stacked bar chart showing power adjustment resources, battery and power plant icons, blue and green colors, professional business chart"
            },
            {
                "id": "section_3",
                "heading": "今後のアクション",
                "icon_hint": "target",
                "color_hint": "success",
                "key_points": [
                    "蓄電池の導入拡大",
                    "デマンドレスポンスの活用促進",
                    "系統増強計画の推進"
                ],
                "detail": None,
                "image_prompt_en": "flat infographic style, target icon with checkmarks, roadmap showing three action items, green and white colors, clean minimalist design"
            }
        ],
        "footer_note": "出典：社内資料より作成"
    }
    return json.dumps(example, ensure_ascii=False, indent=2)
