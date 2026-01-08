"""
Slide Generator service for creating PowerPoint slides using LLM.

This module provides functions to:
- Generate slide structures from text content
- Refine slides based on user instructions
- Manage slide generation projects
"""
import logging
import json
from typing import List, Dict, Optional, Any, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.slide_project import SlideProject, SlideContent, SlideMessage
from app.models.llm_settings import LLMSettings
from app.services.llm_client import call_generation_llm
from app.services.json_parser import extract_json_from_response

logger = logging.getLogger(__name__)

# System prompt for slide generation
SLIDE_GENERATION_SYSTEM_PROMPT = """あなたはプレゼンテーション資料の専門家です。
与えられたテキストから、効果的なPowerPointスライドの構成を作成してください。

【スライド設計の原則】
1. 各スライドは1つの明確なメッセージに集中
2. 箇条書きは3〜5項目が最適（多くても7項目まで）
3. タイトルは簡潔で内容を的確に表現
4. 発表者ノートには話すべきポイントや補足情報を記載

【スライドタイプ】
- title: タイトルスライド（最初のスライド）
- section: セクション区切り（新しいトピックの開始）
- content: 通常のコンテンツスライド
- conclusion: まとめ・結論（最後のスライド）

【出力形式】
以下のJSON形式で出力してください：

```json
{{
  "slides": [
    {{
      "slide_number": 1,
      "slide_type": "title",
      "title": "プレゼンテーションタイトル",
      "content": {{
        "subtitle": "サブタイトル（任意）",
        "bullets": []
      }},
      "speaker_notes": "このプレゼンテーションでは..."
    }},
    {{
      "slide_number": 2,
      "slide_type": "content",
      "title": "セクションタイトル",
      "content": {{
        "bullets": ["ポイント1", "ポイント2", "ポイント3"],
        "details": "詳細説明（任意）"
      }},
      "speaker_notes": "このスライドでは以下のポイントを説明します..."
    }}
  ]
}}
```

【重要】
- 必ず有効なJSON形式で出力してください
- スライド番号は1から順番に振ってください
- 内容が薄いスライドは作らないでください
- 発表者ノートは具体的に記載してください"""

SLIDE_GENERATION_USER_TEMPLATE = """以下のテキストからPowerPointスライドを作成してください。

【入力テキスト】
{source_text}

【条件】
- タイトル: {title}
{slide_count_instruction}
{key_points_instruction}

上記の内容に基づいて、効果的なスライド構成をJSON形式で出力してください。"""

# System prompt for slide refinement
SLIDE_REFINEMENT_SYSTEM_PROMPT = """あなたはプレゼンテーション資料の専門家です。
ユーザーの指示に基づいて、既存のスライド構成を修正・改善してください。

【修正のルール】
1. ユーザーの指示に忠実に従う
2. 指示されていない部分は変更しない
3. スライド番号は常に1から連番で振り直す
4. 修正後も全体の流れが自然になるよう調整

【出力形式】
修正後のスライド構成全体をJSON形式で出力してください。
フォーマットは生成時と同じです。

【重要】
- 必ず有効なJSON形式で出力してください
- 全てのスライドを含めてください（変更のないスライドも）"""

SLIDE_REFINEMENT_USER_TEMPLATE = """【現在のスライド構成】
```json
{current_slides}
```

【修正指示】
{instruction}

上記の指示に基づいて、修正後のスライド構成全体をJSON形式で出力してください。"""


def get_slide_generation_prompts(db: Optional[Session]) -> Tuple[Optional[str], Optional[str]]:
    """
    Get custom slide generation prompts from LLM settings.

    Args:
        db: Database session (optional)

    Returns:
        Tuple of (system_prompt, user_template), both can be None if using defaults
    """
    if db is None:
        return None, None

    # Get system-level LLM settings (user_id is NULL)
    settings_record = db.query(LLMSettings).filter(LLMSettings.user_id.is_(None)).first()

    if not settings_record or not settings_record.prompt_settings:
        return None, None

    prompt_settings = settings_record.prompt_settings
    system_prompt = prompt_settings.get("slide_generation_system")
    user_template = prompt_settings.get("slide_generation_user")

    return system_prompt, user_template


def get_slide_refinement_prompts(db: Optional[Session]) -> Tuple[Optional[str], Optional[str]]:
    """
    Get custom slide refinement prompts from LLM settings.

    Args:
        db: Database session (optional)

    Returns:
        Tuple of (system_prompt, user_template), both can be None if using defaults
    """
    if db is None:
        return None, None

    # Get system-level LLM settings (user_id is NULL)
    settings_record = db.query(LLMSettings).filter(LLMSettings.user_id.is_(None)).first()

    if not settings_record or not settings_record.prompt_settings:
        return None, None

    prompt_settings = settings_record.prompt_settings
    system_prompt = prompt_settings.get("slide_refinement_system")
    user_template = prompt_settings.get("slide_refinement_user")

    return system_prompt, user_template


async def generate_slides(
    source_text: str,
    title: str,
    target_slide_count: Optional[int] = None,
    key_points: Optional[str] = None,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    Generate slide structure from source text using LLM.

    Args:
        source_text: Text content to convert to slides
        title: Title for the presentation
        target_slide_count: Optional target number of slides
        key_points: Optional key points to emphasize
        db: Optional database session for getting custom prompts

    Returns:
        Dict with 'slides' key containing list of slide dicts
    """
    # Build conditional instructions
    slide_count_instruction = ""
    if target_slide_count:
        slide_count_instruction = f"- 目標スライド数: {target_slide_count}枚程度"
    else:
        slide_count_instruction = "- スライド数: 内容に応じて適切な枚数"

    key_points_instruction = ""
    if key_points:
        key_points_instruction = f"- 重点ポイント: {key_points}"

    # Get custom prompts if available
    custom_system, custom_user = get_slide_generation_prompts(db)
    system_prompt = custom_system if custom_system else SLIDE_GENERATION_SYSTEM_PROMPT
    user_template = custom_user if custom_user else SLIDE_GENERATION_USER_TEMPLATE

    user_message = user_template.format(
        source_text=source_text,
        title=title,
        slide_count_instruction=slide_count_instruction,
        key_points_instruction=key_points_instruction,
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    try:
        response = await call_generation_llm(messages, temperature=0.3)
        json_str = extract_json_from_response(response)

        # Parse the JSON string
        try:
            result = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}, content: {json_str[:500]}")
            raise ValueError(f"Invalid JSON in LLM response: {e}")

        if not isinstance(result, dict) or "slides" not in result:
            logger.warning(f"Unexpected response format: {type(result)}")
            # Try to wrap if it's a list
            if isinstance(result, list):
                result = {"slides": result}
            else:
                raise ValueError("Invalid response format from LLM")

        # Validate and clean slides
        slides = _validate_slides(result.get("slides", []))
        result["slides"] = slides

        logger.info(f"Generated {len(slides)} slides")
        return result

    except Exception as e:
        logger.error(f"Slide generation failed: {e}", exc_info=True)
        raise


async def refine_slides(
    current_slides: List[Dict],
    instruction: str,
    chat_history: Optional[List[Dict]] = None,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    Refine existing slides based on user instruction.

    Args:
        current_slides: Current slide structure
        instruction: User's refinement instruction
        chat_history: Optional previous chat messages for context
        db: Optional database session for getting custom prompts

    Returns:
        Dict with 'slides' key containing updated slide list
    """
    current_slides_json = json.dumps(current_slides, ensure_ascii=False, indent=2)

    # Get custom prompts if available
    custom_system, custom_user = get_slide_refinement_prompts(db)
    system_prompt = custom_system if custom_system else SLIDE_REFINEMENT_SYSTEM_PROMPT
    user_template = custom_user if custom_user else SLIDE_REFINEMENT_USER_TEMPLATE

    user_message = user_template.format(
        current_slides=current_slides_json,
        instruction=instruction,
    )

    messages = [
        {"role": "system", "content": system_prompt},
    ]

    # Add chat history for context
    if chat_history:
        for msg in chat_history[-6:]:  # Keep last 6 messages for context
            messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": user_message})

    try:
        response = await call_generation_llm(messages, temperature=0.2)
        json_str = extract_json_from_response(response)

        # Parse the JSON string
        try:
            result = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}, content: {json_str[:500]}")
            raise ValueError(f"Invalid JSON in LLM response: {e}")

        if not isinstance(result, dict) or "slides" not in result:
            if isinstance(result, list):
                result = {"slides": result}
            else:
                raise ValueError("Invalid response format from LLM")

        # Validate and clean slides
        slides = _validate_slides(result.get("slides", []))
        result["slides"] = slides

        logger.info(f"Refined slides, now {len(slides)} slides")
        return result

    except Exception as e:
        logger.error(f"Slide refinement failed: {e}", exc_info=True)
        raise


def _validate_slides(slides: List[Dict]) -> List[Dict]:
    """
    Validate and clean slide data.

    Args:
        slides: List of slide dicts from LLM

    Returns:
        Cleaned and validated slide list
    """
    valid_slides = []
    valid_types = {"title", "section", "content", "conclusion"}

    for i, slide in enumerate(slides):
        if not isinstance(slide, dict):
            continue

        # Ensure required fields
        if not slide.get("title"):
            continue

        # Clean and validate
        cleaned = {
            "slide_number": i + 1,  # Re-number sequentially
            "slide_type": slide.get("slide_type", "content"),
            "title": str(slide.get("title", "")),
            "content": slide.get("content", {}),
            "speaker_notes": slide.get("speaker_notes", ""),
        }

        # Validate slide type
        if cleaned["slide_type"] not in valid_types:
            cleaned["slide_type"] = "content"

        # Ensure content is a dict
        if not isinstance(cleaned["content"], dict):
            cleaned["content"] = {"bullets": [], "details": str(cleaned["content"])}

        # Ensure bullets is a list
        if "bullets" not in cleaned["content"]:
            cleaned["content"]["bullets"] = []
        elif not isinstance(cleaned["content"]["bullets"], list):
            cleaned["content"]["bullets"] = [str(cleaned["content"]["bullets"])]

        valid_slides.append(cleaned)

    return valid_slides


async def process_slide_generation(
    db: Session,
    project_id: UUID,
) -> None:
    """
    Process slide generation for a project.

    Args:
        db: Database session
        project_id: Project UUID
    """
    logger.info(f"Processing slide generation for project_id={project_id}")

    project = db.query(SlideProject).filter(SlideProject.id == project_id).first()
    if not project:
        logger.error(f"Project not found: {project_id}")
        return

    try:
        project.status = "generating"
        db.commit()

        # Generate slides
        result = await generate_slides(
            source_text=project.source_text,
            title=project.title,
            target_slide_count=project.target_slide_count,
            key_points=project.key_points,
            db=db,
        )

        # Clear existing slides
        db.query(SlideContent).filter(SlideContent.project_id == project_id).delete()

        # Save new slides
        for slide_data in result.get("slides", []):
            slide = SlideContent(
                project_id=project_id,
                slide_number=slide_data["slide_number"],
                slide_type=slide_data["slide_type"],
                title=slide_data["title"],
                content=slide_data["content"],
                speaker_notes=slide_data.get("speaker_notes", ""),
            )
            db.add(slide)

        project.status = "completed"
        db.commit()

        logger.info(f"Slide generation completed for project {project_id}")

    except Exception as e:
        logger.error(f"Slide generation failed: {e}", exc_info=True)
        project.status = "failed"
        project.error_message = str(e)
        db.commit()


async def process_slide_generation_background(project_id: UUID) -> None:
    """
    Background task wrapper for slide generation.

    Args:
        project_id: Project UUID
    """
    logger.info(f"Starting background slide generation for {project_id}")
    db = SessionLocal()
    try:
        await process_slide_generation(db, project_id)
    finally:
        db.close()
        logger.info(f"Background slide generation completed for {project_id}")
