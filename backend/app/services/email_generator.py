"""
Email Generator service for generating email content from documents and meeting minutes.

This module handles the generation of email body text that summarizes documents
and extracts speaker opinions from meeting minutes using RAG context and LLM.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, LLMConnectionError
from app.models.llm_settings import LLMSettings
from app.schemas.email import EmailContent, EmailGenerateResponse, SpeakerOpinion
from app.services.context_retriever import (
    format_summaries_for_prompt,
    retrieve_summaries_for_email,
)
from app.services.json_parser import parse_llm_json
from app.services.llm_client import call_generation_llm

logger = logging.getLogger(__name__)


# System prompt for email generation
EMAIL_SYSTEM_PROMPT = """あなたは社内コミュニケーションの専門家です。
資料と議事録から、関係者への周知メールを作成します。

## 最重要：出力言語
・全ての値は必ず日本語で出力してください
・英語での出力は禁止です
・JSONのキー名のみ英語を使用し、値（文章・名前・意見）は全て日本語で記載してください

## 発言者の話しぶりを残す【重要】
speaker_opinionsの意見は、発言者の言葉遣いや口調をできるだけ保持してください。
・元の発言のキーフレーズや特徴的な表現はそのまま使う
・「〜と思います」「〜ではないでしょうか」などの語尾も残す
・強い主張、懸念、提案などのトーンが伝わるようにする

良い例：
・「このスケジュールでは厳しいのではないか」（懸念のトーンが伝わる）
・「ぜひ進めるべきだと思います」（積極的な姿勢が伝わる）
・「予算面での課題をクリアできれば問題ない」（条件付き賛成が伝わる）

悪い例：
・「スケジュールに懸念」（話しぶりが消えている）
・「賛成」（ニュアンスが消えている）

## 出力形式【絶対遵守】
以下の英語キー名のJSONスキーマに従って出力してください。
キー名は英語、値は日本語です。

{
  "document_summary": "資料の要約文（3〜5文、必須）",
  "speaker_opinions": [
    {"speaker": "発言者名", "opinions": ["話しぶりを残した意見1", "話しぶりを残した意見2"]}
  ],
  "additional_notes": "補足事項（任意、不要ならnull）"
}

## 日本語出力の例
{
  "document_summary": "本資料では、新システムの導入計画について説明しています。導入時期は来年4月を予定しており、予算は500万円を見込んでいます。",
  "speaker_opinions": [
    {"speaker": "田中部長", "opinions": ["このスケジュールでは厳しいのではないか", "予算についてはもう少し精査が必要だと思う"]},
    {"speaker": "佐藤課長", "opinions": ["技術的な課題はクリアできる見込みです", "ぜひ進めていきたい"]}
  ],
  "additional_notes": "次回会議で詳細を決定予定"
}

## 出力ルール
・JSONのみを出力。説明文やマークダウン記法は不要
・キー名は英語、値は必ず日本語
・document_summaryは空にしない
・speaker_opinionsは空配列にしない
・議事録に登場する全ての発言者を抽出すること（省略しない）
・各発言者の意見は話しぶり（トーン、ニュアンス）を残して記載
"""

EMAIL_USER_TEMPLATE = """以下は社内資料と議事録の要約です：

【資料の要約】
{document_context}

【議事録の要約】
{minutes_context}

---

この内容をもとに、以下のトピックに関する周知メールの内容を日本語で生成してください。

【トピック】
{topic}

【重要：発言者の話しぶりを残す】
・発言者の言葉遣いや口調をできるだけ保持する
・「〜と思う」「〜ではないか」などの語尾も残す
・例：「厳しいのではないか」「ぜひ進めたい」のように話しぶりを残す

【要件】
・資料からは要点を簡潔にまとめてdocument_summaryに記載
・議事録からは全ての発言者を抽出し、話しぶりを残した意見をspeaker_opinionsに記載
・発言者を省略せず、議事録に登場する人物全員の意見を含める

【出力形式】JSONのみ出力（値は全て日本語、発言者の話しぶりを残す）:
{{"document_summary": "要約文", "speaker_opinions": [{{"speaker": "名前", "opinions": ["話しぶりを残した意見"]}}], "additional_notes": null}}"""


def get_email_prompts(db: Session) -> Tuple[Optional[str], Optional[str]]:
    """
    Get custom email prompts from LLM settings.

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
    system_prompt = prompt_settings.get("email_system")
    user_template = prompt_settings.get("email_user")

    return system_prompt, user_template


def _format_email_body(topic: str, content: EmailContent) -> str:
    """
    Format the structured content into a readable email body.

    Args:
        topic: Email topic
        content: Structured email content

    Returns:
        Formatted email body as plain text
    """
    lines = []

    # Subject line
    lines.append(f"件名: {topic}")
    lines.append("")

    # Document summary section
    if content.document_summary:
        lines.append("【資料の要約】")
        lines.append(content.document_summary)
        lines.append("")

    # Speaker opinions section
    if content.speaker_opinions:
        lines.append("【議事録からの意見（発言者別）】")
        lines.append("")

        for opinion in content.speaker_opinions:
            lines.append(f"■ {opinion.speaker}")
            for item in opinion.opinions:
                lines.append(f"  - {item}")
            lines.append("")

    # Additional notes section
    if content.additional_notes:
        lines.append("【補足事項】")
        lines.append(content.additional_notes)
        lines.append("")

    return "\n".join(lines)


async def generate_email_content(
    db: Session,
    notebook_id: UUID,
    topic: str,
    document_source_ids: List[UUID],
    minute_ids: List[UUID],
    user_id: UUID,
) -> EmailGenerateResponse:
    """
    Generate email content from documents and meeting minutes using LLM.

    Args:
        db: Database session
        notebook_id: Target notebook UUID
        topic: Topic/subject of the email
        document_source_ids: List of document source UUIDs
        minute_ids: List of minute UUIDs (text-based meeting minutes)
        user_id: User ID for permission validation

    Returns:
        EmailGenerateResponse with generated email body and structured content

    Raises:
        BadRequestError: If context retrieval or JSON parsing fails
        LLMConnectionError: If LLM service is unavailable
    """
    logger.info(f"Generating email for notebook {notebook_id}, topic: {topic[:50]}...")

    if not document_source_ids and not minute_ids:
        raise BadRequestError(
            "メール生成には少なくとも1つの資料または議事録を選択してください。"
        )

    # 1. Retrieve summaries from documents and minutes
    logger.info(
        f"Retrieving summaries from {len(document_source_ids)} documents and {len(minute_ids)} minutes"
    )
    summary_result = await retrieve_summaries_for_email(
        db=db,
        notebook_id=notebook_id,
        source_ids=document_source_ids if document_source_ids else None,
        minute_ids=minute_ids if minute_ids else None,
        user_id=user_id,
    )

    # Log any pending sources/minutes (still being processed)
    if summary_result.pending_sources:
        logger.warning(
            f"Some sources are still processing: {summary_result.pending_sources}"
        )
    if summary_result.pending_minutes:
        logger.warning(
            f"Some minutes are still processing: {summary_result.pending_minutes}"
        )

    # 2. Format summaries for prompt
    document_context_text, minutes_context_text = format_summaries_for_prompt(
        summary_result
    )
    logger.info(
        f"Context lengths: documents={len(document_context_text)} chars, "
        f"minutes={len(minutes_context_text)} chars"
    )

    # Check if we have any context
    if not document_context_text and not minutes_context_text:
        raise BadRequestError(
            "選択されたソースからコンテキストを取得できませんでした。"
            "ソースにテキストが含まれているか確認してください。"
        )

    # 3. Build LLM messages with custom prompts if available
    custom_system, custom_user = get_email_prompts(db)
    system_prompt = custom_system if custom_system else EMAIL_SYSTEM_PROMPT
    user_template = custom_user if custom_user else EMAIL_USER_TEMPLATE

    user_content = user_template.format(
        document_context=document_context_text or "(資料なし)",
        minutes_context=minutes_context_text or "(議事録なし)",
        topic=topic,
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    # 4. Call LLM
    try:
        raw_response = await call_generation_llm(messages, temperature=0.3)
        logger.info(f"LLM response length: {len(raw_response)} chars")
        # Note: Raw response not logged to avoid leaking user data in logs
    except Exception as e:
        logger.error(f"LLM call failed for email generation: {e}")
        raise LLMConnectionError(f"LLMサービスへの接続に失敗しました: {str(e)}")

    # 5. Parse and validate JSON response
    content = parse_llm_json(raw_response, EmailContent)
    logger.info(
        f"Parsed content: document_summary={len(content.document_summary)} chars, "
        f"speaker_opinions={len(content.speaker_opinions)} items, "
        f"additional_notes={'Yes' if content.additional_notes else 'No'}"
    )

    # 5.1 Validate that we have meaningful content
    if not content.document_summary and not content.speaker_opinions:
        logger.warning(
            f"LLM returned empty content (response length: {len(raw_response)} chars)"
        )
        # Instead of raising an error, provide a fallback message
        if document_context_text or minutes_context_text:
            logger.info("Generating fallback content from retrieved context")
            # Create fallback content
            fallback_summary = "提供された資料・議事録の内容をご確認ください。"
            if document_context_text:
                fallback_summary = (
                    document_context_text[:500] + "..."
                    if len(document_context_text) > 500
                    else document_context_text
                )

            content = EmailContent(
                document_summary=fallback_summary,
                speaker_opinions=(
                    [
                        SpeakerOpinion(
                            speaker="参加者",
                            opinions=["詳細は添付の資料・議事録をご確認ください。"],
                        )
                    ]
                    if minutes_context_text
                    else []
                ),
                additional_notes="※AIによる要約生成に問題が発生したため、原文の一部を表示しています。",
            )

    # 6. Format email body
    email_body = _format_email_body(topic, content)
    logger.debug(f"Formatted email body length: {len(email_body)} chars")

    # 7. Build response
    sources_used = len(document_source_ids) + len(minute_ids)

    logger.info(
        f"Successfully generated email with {len(content.speaker_opinions)} speakers"
    )

    return EmailGenerateResponse(
        topic=topic,
        email_body=email_body,
        content=content,
        sources_used=sources_used,
        generated_at=datetime.now(timezone.utc),
    )
