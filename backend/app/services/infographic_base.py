"""
Base module for infographic generation.

This module provides shared functionality for generating infographics:
- Common prompt components (icon hints, color hints)
- Common LLM call and JSON parsing flow
- Post-processing utilities
"""

import logging
from typing import Any, Awaitable, Callable, List

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, LLMConnectionError
from app.schemas.infographic import InfographicStructure
from app.services.json_parser import parse_llm_json
from app.services.llm_client import call_generation_llm

logger = logging.getLogger(__name__)


# =============================================================================
# Common Constants
# =============================================================================

# Valid icon hints for infographic sections
VALID_ICON_HINTS = [
    "lightbulb",  # アイデア・ポイント
    "chart",  # データ・統計
    "target",  # 目標・ゴール
    "users",  # 人・チーム
    "shield",  # 安全・セキュリティ
    "clock",  # 時間・スケジュール
    "warning",  # 注意・リスク
    "check",  # 完了・確認
    "arrow",  # プロセス・流れ
    "star",  # 重要・おすすめ
]

# Valid color hints for infographic sections
VALID_COLOR_HINTS = [
    "primary",  # メイン色・青系
    "secondary",  # サブ色・グレー系
    "accent",  # アクセント色・紫系
    "success",  # 成功・緑系
    "warning",  # 警告・黄色系
    "danger",  # 危険・赤系
]

# Common icon hint documentation for system prompts
ICON_HINT_DOCS = """## icon_hint で使用可能な値
- lightbulb（アイデア・ポイント）
- chart（データ・統計）
- target（目標・ゴール）
- users（人・チーム）
- shield（安全・セキュリティ）
- clock（時間・スケジュール）
- warning（注意・リスク）
- check（完了・確認）
- arrow（プロセス・流れ）
- star（重要・おすすめ）"""

# Common color hint documentation for system prompts
COLOR_HINT_DOCS = """## color_hint で使用可能な値
- primary（メイン色・青系）
- secondary（サブ色・グレー系）
- accent（アクセント色・紫系）
- success（成功・緑系）
- warning（警告・黄色系）
- danger（危険・赤系）"""

# Common rules for content detail (used in both system prompts)
CONTENT_DETAIL_RULES = """## 内容の詳細化に関する重要ルール
- 各key_pointは短い箇条書きではなく、内容がわかる説明文にする
- 「何が」「なぜ」「どのように」を含めて記述する
- 背景や理由、影響・効果なども含めて詳しく説明する
- 抽象的な表現（「改善した」「向上した」等）だけでなく、具体的な内容を記述する
- detailには、そのセクションの背景・文脈・補足情報を詳しく記載する"""

# Common image prompt guidelines
IMAGE_PROMPT_GUIDELINES = """## image_prompt_en の書き方
- 英語で記述
- フラットなインフォグラフィックスタイルを指定
- 具体的な視覚要素を含める
- 例: "flat infographic style, minimal design, pie chart showing 60% renewable energy, green and blue colors, clean white background, professional business presentation\""""

# Common output rules
OUTPUT_RULES = """## 出力ルール
1. 必ず有効なJSONのみを出力してください。説明文やマークダウンは不要です。
2. セクションは4〜8個を目安にしてください（情報量に応じて増減可）。
3. 各セクションには以下を含めてください：
   - 見出し（heading）: 具体的で内容を正確に表す
   - アイコンヒント（icon_hint）
   - キーポイント（key_points）: 4〜6個、各ポイントは内容を詳しく説明する
   - 詳細説明（detail）: 必ず記載。背景情報や補足説明を50〜150文字程度で記述
   - 画像プロンプト（image_prompt_en）
4. 日本語テキスト出力。ただし image_prompt_en は必ず英語で記述してください。
5. 各セクションに image_prompt_en を必ず含めてください（画像生成用の英語プロンプト）。"""


# =============================================================================
# Helper Functions
# =============================================================================


def build_system_prompt(domain: str, additional_rules: str = "") -> str:
    """
    Build a system prompt for infographic generation.

    Args:
        domain: The domain description (e.g., "社内資料", "審議会資料・議事録")
        additional_rules: Additional domain-specific rules

    Returns:
        Complete system prompt string
    """
    base_intro = f"""あなたは{domain}の構成を専門的に設計する情報アーキテクト兼デザイナーです。

【重要】いきなりJSONを生成せず、以下のステップで深く考えてください：

1. まず資料全体の論点・ストーリーラインを整理する
2. 「1枚のインフォグラフィックとして最も伝わりやすい構成」を決める
3. 各セクションに適切なビジュアル（図解）を計画する
4. 最後に構成要素をJSONで出力する
"""

    bad_good_example = """## 悪い例と良い例
- 悪い例: 「コスト削減」「効率化を実現」「品質向上」
- 良い例: 「業務プロセスの見直しにより、従来3日かかっていた承認フローを1日に短縮し、担当者の負担を軽減」"""

    sections = [
        base_intro,
        OUTPUT_RULES,
        CONTENT_DETAIL_RULES,
        additional_rules if additional_rules else "",
        bad_good_example,
        IMAGE_PROMPT_GUIDELINES,
        ICON_HINT_DOCS,
        COLOR_HINT_DOCS,
    ]

    return "\n\n".join(s for s in sections if s)


def build_user_template(source_description: str, footer_note: str) -> str:
    """
    Build a user message template for infographic generation.

    Args:
        source_description: Description of the source content
        footer_note: Default footer note text

    Returns:
        User template string with {context} and {topic} placeholders
    """
    return f"""以下は{source_description}から抽出した関連部分です：

---
{{context}}
---

この内容をもとに、以下のトピックに関する1ページのインフォグラフィック構造を生成してください。

【トピック】
{{topic}}

【出力JSONスキーマ】
{{{{
  "title": "インフォグラフィックのタイトル",
  "subtitle": "サブタイトル（省略可）",
  "sections": [
    {{{{
      "id": "section_1",
      "heading": "セクション見出し（具体的に）",
      "icon_hint": "lightbulb",
      "color_hint": "primary",
      "key_points": [
        "内容を詳しく説明するポイント1（何が、なぜ、どのようにを含む）",
        "内容を詳しく説明するポイント2",
        "内容を詳しく説明するポイント3",
        "内容を詳しく説明するポイント4"
      ],
      "detail": "このセクションの背景・文脈・補足情報を詳しく記述（必須、50〜150文字）",
      "image_prompt_en": "flat infographic style, minimal design, lightbulb icon with innovation concept, blue and white colors, clean background"
    }}}}
  ],
  "footer_note": "{footer_note}"
}}}}

【重要：概要をまとめつつ、内容を詳細に】
- セクション数: 4〜8個（資料の情報量に応じて）
- key_points: 各セクション4〜6個（短い箇条書きではなく、内容がわかる説明文）
- detail: 必ず記載（背景・理由・文脈を含む詳しい説明）
- 抽象的な表現（「改善」「向上」等）だけでなく、具体的な内容を記述する
- 各セクションに image_prompt_en を必ず含める（英語）

JSONのみを出力してください："""


def postprocess_infographic_structure(
    structure: InfographicStructure,
) -> InfographicStructure:
    """
    Post-process an infographic structure.

    Ensures all sections have IDs and validates structure.

    Args:
        structure: The parsed infographic structure

    Returns:
        Post-processed structure
    """
    for i, section in enumerate(structure.sections):
        if not section.id:
            section.id = f"section_{i + 1}"

    return structure


async def generate_infographic_from_context(
    context_text: str,
    topic: str,
    system_prompt: str,
    user_template: str,
    domain_name: str,
    temperature: float = 0.3,
) -> InfographicStructure:
    """
    Generate an infographic structure from context using LLM.

    This is the core generation function used by both notebook and council
    infographic generators.

    Args:
        context_text: Formatted context text from sources
        topic: Topic/prompt describing what the infographic should cover
        system_prompt: System prompt for the LLM
        user_template: User message template (must contain {context} and {topic})
        domain_name: Domain name for logging (e.g., "notebook", "council")
        temperature: LLM temperature parameter

    Returns:
        InfographicStructure with generated content

    Raises:
        LLMConnectionError: If LLM service is unavailable
        BadRequestError: If JSON parsing fails
    """
    # Build LLM messages
    user_content = user_template.format(
        context=context_text,
        topic=topic,
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    # Call LLM
    try:
        raw_response = await call_generation_llm(messages, temperature=temperature)
    except Exception as e:
        logger.error(f"LLM call failed for {domain_name} infographic generation: {e}")
        raise LLMConnectionError(f"LLMサービスへの接続に失敗しました: {str(e)}")

    # Parse and validate JSON response
    structure = parse_llm_json(raw_response, InfographicStructure)

    # Post-process
    structure = postprocess_infographic_structure(structure)

    logger.info(
        f"Successfully generated {domain_name} infographic with {len(structure.sections)} sections"
    )
    return structure
