"""
Document Checker service for detecting issues in documents using LLM.

This module provides functions to check documents for:
- Typos (誤字脱字)
- Grammar errors (文法エラー)
- Expression improvements (表現改善)
- Consistency issues (表記ゆれ)
- Terminology (専門用語)
- Honorific usage (敬語・丁寧語)
- Readability (読みやすさ)
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.document_check import DocumentCheck, DocumentCheckIssue
from app.models.llm_settings import LLMSettings
from app.services.json_parser import extract_json_from_response
from app.services.llm_client import call_generation_llm

logger = logging.getLogger(__name__)

# Available check types with descriptions
CHECK_TYPES: Dict[str, Dict[str, Any]] = {
    "typo": {
        "id": "typo",
        "name": "誤字脱字",
        "description": "タイプミス、変換ミス、脱字を検出します",
        "default_enabled": True,
        "prompt_instruction": "誤字脱字（タイプミス、変換ミス、脱字）を検出してください。",
    },
    "grammar": {
        "id": "grammar",
        "name": "文法エラー",
        "description": "助詞の誤り、文法的な間違いを検出します",
        "default_enabled": True,
        "prompt_instruction": "文法エラー（助詞の誤り、文法的な間違い、主語と述語の不一致）を検出してください。",
    },
    "expression": {
        "id": "expression",
        "name": "表現改善",
        "description": "より適切な表現や言い回しを提案します",
        "default_enabled": True,
        "prompt_instruction": "より適切な表現や言い回しがある場合は提案してください。ただし、好みの問題に過ぎないものは指摘しないでください。",
    },
    "consistency": {
        "id": "consistency",
        "name": "表記ゆれ",
        "description": "同じ概念の表記統一（例：サーバー/サーバ）を検出します",
        "default_enabled": True,
        "prompt_instruction": "表記ゆれ（同じ概念の異なる表記、例：サーバー/サーバ、ユーザー/ユーザ）を検出してください。",
    },
    "terminology": {
        "id": "terminology",
        "name": "専門用語",
        "description": "業界・組織固有の用語チェック（カスタム辞書対応）",
        "default_enabled": False,
        "prompt_instruction": "専門用語の誤用や不適切な使用を検出してください。",
    },
    "honorific": {
        "id": "honorific",
        "name": "敬語・丁寧語",
        "description": "敬語の誤り、敬語レベルの一貫性を検出します",
        "default_enabled": False,
        "prompt_instruction": "敬語の誤り（二重敬語、敬語の過不足）や敬語レベルの一貫性を検出してください。",
    },
    "readability": {
        "id": "readability",
        "name": "読みやすさ",
        "description": "文の長さ、複雑な構文の改善提案",
        "default_enabled": False,
        "prompt_instruction": "読みやすさの観点から、長すぎる文や複雑な構文を指摘してください。",
    },
}

# System prompt for document checking
DOCUMENT_CHECK_SYSTEM_PROMPT = """あなたは日本語文書の校正専門家です。
与えられたテキストを分析し、問題点を指摘してください。

【チェック対象】
{check_instructions}

【重要な注意事項】
・明らかな問題のみを指摘してください。好みや文体の問題は指摘しないでください。
・問題がない場合は無理に指摘を作らないでください。
・各問題には具体的な修正案と理由を含めてください。
・original_text には問題のある箇所を含む文または段落を引用してください。

【出力形式】
以下のJSON配列形式で出力してください。問題がない場合は空の配列 [] を返してください。

```json
[
  {{
    "category": "typo|grammar|expression|consistency|terminology|honorific|readability",
    "severity": "error|warning|info",
    "page_or_slide": null,
    "original_text": "問題のある箇所を含む文",
    "suggested_text": "修正後の文",
    "explanation": "なぜ問題なのか、どう直すべきかの説明"
  }}
]
```

severity の基準:
・error: 明らかな誤り（誤字脱字、文法エラー）
・warning: 改善が推奨される問題（表記ゆれ、表現改善）
・info: 参考情報（読みやすさの提案など）"""

DOCUMENT_CHECK_USER_TEMPLATE = """以下のテキストをチェックしてください。

---
{text}
---

問題点をJSON配列で出力してください。問題がない場合は [] を返してください。"""


# Maximum text length for a single LLM call
MAX_CHECK_TEXT_LENGTH = 8000


def get_document_check_prompts(
    db: Optional[Session],
) -> Tuple[Optional[str], Optional[str]]:
    """
    Get custom document check prompts from LLM settings.

    Args:
        db: Database session (optional)

    Returns:
        Tuple of (system_prompt, user_template), both can be None if using defaults
    """
    if db is None:
        return None, None

    # Get system-level LLM settings (user_id is NULL)
    settings_record = (
        db.query(LLMSettings).filter(LLMSettings.user_id.is_(None)).first()
    )

    if not settings_record or not settings_record.prompt_settings:
        return None, None

    prompt_settings = settings_record.prompt_settings
    system_prompt = prompt_settings.get("document_check_system")
    user_template = prompt_settings.get("document_check_user")

    return system_prompt, user_template


def get_default_check_types() -> List[str]:
    """Get list of check types that are enabled by default."""
    return [
        check_id
        for check_id, check_info in CHECK_TYPES.items()
        if check_info.get("default_enabled", False)
    ]


def get_check_types_info() -> List[Dict[str, Any]]:
    """Get information about all available check types."""
    return [
        {
            "id": check_info["id"],
            "name": check_info["name"],
            "description": check_info["description"],
            "default_enabled": check_info["default_enabled"],
        }
        for check_info in CHECK_TYPES.values()
    ]


def _build_check_instructions(enabled_check_types: List[str]) -> str:
    """Build the check instructions section of the prompt."""
    instructions = []
    for check_type in enabled_check_types:
        if check_type in CHECK_TYPES:
            check_info = CHECK_TYPES[check_type]
            instructions.append(
                f"・{check_info['name']}: {check_info['prompt_instruction']}"
            )
    return "\n".join(instructions)


async def check_document_text(
    text: str,
    enabled_check_types: List[str],
    custom_terminology: Optional[Dict[str, str]] = None,
    db: Optional[Session] = None,
) -> List[Dict[str, Any]]:
    """
    Check document text for issues using LLM.

    Args:
        text: Document text to check
        enabled_check_types: List of enabled check type IDs
        custom_terminology: Optional custom terminology dictionary
        db: Optional database session for getting custom prompts

    Returns:
        List of detected issues
    """
    if not text or not text.strip():
        return []

    if not enabled_check_types:
        enabled_check_types = get_default_check_types()

    # Filter to valid check types
    valid_check_types = [ct for ct in enabled_check_types if ct in CHECK_TYPES]
    if not valid_check_types:
        logger.warning("No valid check types provided, using defaults")
        valid_check_types = get_default_check_types()

    # Build check instructions
    check_instructions = _build_check_instructions(valid_check_types)

    # Add custom terminology if provided
    if custom_terminology and "terminology" in valid_check_types:
        terminology_list = ", ".join(
            f"「{term}」→「{correct}」" for term, correct in custom_terminology.items()
        )
        check_instructions += f"\n・カスタム用語辞書: {terminology_list}"

    # Get custom prompts if available
    custom_system, custom_user = get_document_check_prompts(db)

    # Build prompts
    base_system_prompt = (
        custom_system if custom_system else DOCUMENT_CHECK_SYSTEM_PROMPT
    )
    system_prompt = base_system_prompt.format(check_instructions=check_instructions)

    # Truncate text if too long
    text_to_check = text[:MAX_CHECK_TEXT_LENGTH]
    if len(text) > MAX_CHECK_TEXT_LENGTH:
        logger.warning(
            f"Text truncated for checking: {len(text)} -> {MAX_CHECK_TEXT_LENGTH} chars"
        )

    base_user_template = custom_user if custom_user else DOCUMENT_CHECK_USER_TEMPLATE
    user_message = base_user_template.format(text=text_to_check)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    try:
        response = await call_generation_llm(messages, temperature=0.1)
        issues = extract_json_from_response(response)

        if not isinstance(issues, list):
            logger.warning(f"Unexpected response format: {type(issues)}")
            return []

        # Validate and filter issues
        valid_issues = []
        for issue in issues:
            if not isinstance(issue, dict):
                continue

            # Ensure required fields
            if not issue.get("category") or not issue.get("original_text"):
                continue

            # Filter by enabled check types
            if issue.get("category") not in valid_check_types:
                continue

            # Set defaults
            issue.setdefault("severity", "warning")
            issue.setdefault("suggested_text", None)
            issue.setdefault("explanation", None)
            issue.setdefault("page_or_slide", None)

            valid_issues.append(issue)

        logger.info(f"Document check found {len(valid_issues)} issues")
        return valid_issues

    except Exception as e:
        logger.error(f"Document check failed: {e}", exc_info=True)
        raise


async def process_document_check(
    db: Session,
    document_id: UUID,
) -> None:
    """
    Process document check: run LLM check and store results.

    Args:
        db: Database session
        document_id: Document UUID
    """
    logger.info(f"Processing document check for document_id={document_id}")

    # Get document record
    document = db.query(DocumentCheck).filter(DocumentCheck.id == document_id).first()
    if not document:
        logger.error(f"Document not found: {document_id}")
        return

    try:
        # Update status to processing
        document.status = "processing"
        db.commit()

        # Get enabled check types
        enabled_check_types = document.check_types or get_default_check_types()

        # Get user's custom terminology if available
        custom_terminology = None
        if document.user and hasattr(document.user, "check_preferences"):
            prefs = document.user.check_preferences
            if prefs and len(prefs) > 0:
                custom_terminology = prefs[0].custom_terminology

        # Run document check
        logger.info(f"Running LLM check for document {document_id}")
        issues = await check_document_text(
            text=document.original_text,
            enabled_check_types=enabled_check_types,
            custom_terminology=custom_terminology,
            db=db,
        )

        # Store issues
        for issue_data in issues:
            issue = DocumentCheckIssue(
                document_id=document_id,
                category=issue_data["category"],
                severity=issue_data.get("severity", "warning"),
                page_or_slide=issue_data.get("page_or_slide"),
                line_number=issue_data.get("line_number"),
                original_text=issue_data["original_text"],
                suggested_text=issue_data.get("suggested_text"),
                explanation=issue_data.get("explanation"),
            )
            db.add(issue)

        document.status = "completed"
        db.commit()

        logger.info(
            f"Document check completed: {len(issues)} issues found for document {document_id}"
        )

    except Exception as e:
        logger.error(f"Document check failed: {e}", exc_info=True)
        document.status = "failed"
        document.error_message = str(e)
        db.commit()


async def process_document_check_background(document_id: UUID) -> None:
    """
    Background task wrapper for document check processing.

    Creates its own database session for use in FastAPI BackgroundTasks.

    Args:
        document_id: Document UUID
    """
    logger.info(f"Starting background document check for {document_id}")
    db = SessionLocal()
    try:
        await process_document_check(db, document_id)
    finally:
        db.close()
        logger.info(f"Background document check completed for {document_id}")
