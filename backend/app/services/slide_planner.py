"""
Slide Planner service for generating slide deck outlines using LLM.

This module handles the generation of structured JSON slide outlines
from notebook sources using RAG context and LLM.
"""
import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.schemas.slide import SlideOutline
from app.services.context_retriever import retrieve_context, format_context_for_prompt
from app.services.llm_client import call_generation_llm
from app.services.json_parser import parse_llm_json
from app.core.exceptions import BadRequestError, LLMConnectionError

logger = logging.getLogger(__name__)


# System prompt for slide generation
SLIDE_SYSTEM_PROMPT = """あなたは社内説明資料の構成を専門とするシニアコンサルタント兼プレゼンデザイナーです。

【重要】いきなりスライドを列挙せず、以下のステップで深く考えてください：

1. 与えられた情報から「誰に」「何を」「どの順番で」伝えるべきかを整理
2. 章立てを決める（導入 → 現状 → 課題 → 対策 → まとめ）
3. 各章をスライドに落とし込む
4. 各スライドに適切なビジュアルを計画
5. 最後にJSONで出力

## 出力ルール
1. 必ず有効なJSONのみを出力してください。説明文やマークダウンは不要です。
2. 最初のスライドはタイトルスライド（layout: "title"）にしてください。
3. 最後のスライドはまとめスライドにしてください。
4. 各スライドには3〜5個の箇条書きを含めてください。
5. speaker_notes には発表者用のメモを記載してください。
6. visual_hint には「棒グラフで〇〇を比較」のように図表のイメージを記載してください。
7. 日本語テキスト出力。ただし image_prompt_en は必ず英語で記述してください。
8. 図解が必要なスライドには image_prompt_en を含めてください（画像生成用の英語プロンプト）。

## image_prompt_en の書き方
- 英語で記述
- プレゼンテーション用のフラットなスタイルを指定
- 具体的な視覚要素を含める
- 例: "flat presentation style, bar chart comparing year-over-year growth, blue and gray colors, clean professional design, white background"

## layout で使用可能な値
- title（タイトルスライド）
- content（通常のコンテンツスライド）
- section（セクション区切りスライド）
- two_column（2カラムレイアウト）
- blank（白紙・画像用）
"""

SLIDE_USER_TEMPLATE = """以下は社内資料から抽出した関連部分です：

---
{context}
---

この内容をもとに、以下のトピックに関するプレゼンテーション資料の構成案を生成してください。

【トピック】
{topic}

【目標スライド枚数】
{target_slides}枚程度

【出力JSONスキーマ】
{{
  "title": "プレゼンテーションのタイトル",
  "slides": [
    {{
      "slide_number": 1,
      "layout": "title",
      "title": "タイトル",
      "subtitle": "サブタイトル",
      "bullets": null,
      "speaker_notes": "発表者メモ",
      "visual_hint": null,
      "image_prompt_en": null
    }},
    {{
      "slide_number": 2,
      "layout": "content",
      "title": "スライドタイトル",
      "subtitle": null,
      "bullets": ["箇条書き1", "箇条書き2", "箇条書き3"],
      "speaker_notes": "このスライドでは〇〇について説明します。",
      "visual_hint": "棒グラフで年度別推移を表示",
      "image_prompt_en": "flat presentation style, bar chart showing yearly trends, blue and gray colors, professional business chart, clean white background"
    }}
  ]
}}

【重要】
- 図解が効果的なスライドには image_prompt_en を含めてください
- image_prompt_en は英語で、プレゼンテーション用のフラットなスタイルを指定
- タイトルスライドやまとめスライドには画像は不要です

JSONのみを出力してください："""


async def generate_slide_outline(
    db: Session,
    notebook_id: UUID,
    topic: str,
    source_ids: Optional[List[UUID]],
    user_id: UUID,
    target_slides: int = 8,
) -> SlideOutline:
    """
    Generate a slide deck outline from notebook sources using LLM.

    Args:
        db: Database session
        notebook_id: Target notebook UUID
        topic: Topic/prompt describing what the presentation should cover
        source_ids: Optional list of source UUIDs to use for context
        user_id: User ID for permission validation
        target_slides: Target number of slides (default: 8)

    Returns:
        SlideOutline with generated slide structure

    Raises:
        BadRequestError: If context retrieval or JSON parsing fails
        LLMConnectionError: If LLM service is unavailable
    """
    logger.info(
        f"Generating slide outline for notebook {notebook_id}, "
        f"topic: {topic[:50]}..., target: {target_slides} slides"
    )

    # 1. Retrieve context from sources
    context_result = await retrieve_context(
        db=db,
        notebook_id=notebook_id,
        source_ids=source_ids,
        query=topic,
        user_id=user_id,
        top_k=12,  # Get more context for comprehensive slides
    )

    if not context_result.contexts:
        raise BadRequestError(
            "スライド生成に必要なコンテキストが見つかりませんでした。"
            "ノートブックにソースを追加してください。"
        )

    # 2. Format context for prompt
    context_text = format_context_for_prompt(context_result)

    # 3. Build LLM messages
    user_content = SLIDE_USER_TEMPLATE.format(
        context=context_text,
        topic=topic,
        target_slides=target_slides,
    )

    messages = [
        {"role": "system", "content": SLIDE_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    # 4. Call LLM
    try:
        raw_response = await call_generation_llm(messages, temperature=0.3)
    except Exception as e:
        logger.error(f"LLM call failed for slide generation: {e}")
        raise LLMConnectionError(f"LLMサービスへの接続に失敗しました: {str(e)}")

    # 5. Parse and validate JSON response
    outline = parse_llm_json(raw_response, SlideOutline)

    # 6. Post-process: ensure slide numbers are correct
    for i, slide in enumerate(outline.slides):
        slide.slide_number = i + 1

    # 7. Generate images for slides using Janus
    outline = await _generate_images_for_slides(outline, notebook_id)

    logger.info(f"Successfully generated slide outline with {len(outline.slides)} slides")
    return outline


async def _generate_images_for_slides(
    outline: SlideOutline,
    notebook_id: UUID,
) -> SlideOutline:
    """
    Generate images for slides that have image prompts.

    Args:
        outline: The slide outline with image prompts
        notebook_id: Notebook ID for unique filename generation

    Returns:
        Updated outline with image URLs
    """
    from app.services.image_client import generate_slide_image

    for slide in outline.slides:
        if slide.image_prompt_en:
            # Generate unique filename
            filename = f"slide_{notebook_id}_{slide.slide_number}"

            logger.info(
                f"Generating image for slide {slide.slide_number}: "
                f"{slide.image_prompt_en[:50]}..."
            )

            image_url = await generate_slide_image(
                prompt=slide.image_prompt_en,
                output_filename=filename,
                seed=slide.slide_number,
            )

            if image_url:
                slide.image_url = image_url
                logger.info(f"Generated image for slide {slide.slide_number}: {image_url}")
            else:
                logger.warning(f"Failed to generate image for slide {slide.slide_number}")

    return outline
