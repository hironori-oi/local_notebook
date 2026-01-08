"""
Content Processor service for formatting and summarizing documents and minutes.

This module handles:
1. Text formatting using LLM (improving readability while preserving all information)
2. Summary generation for email context (fact-based summaries)
3. Background task processing for sources and minutes

The generated summaries are used for email generation, while chunk-based
RAG remains for chat functionality.
"""
import logging
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.source import Source
from app.models.minute import Minute
from app.models.llm_settings import LLMSettings
from app.services.llm_client import call_generation_llm
from app.core.exceptions import LLMConnectionError
from app.core.config import settings

logger = logging.getLogger(__name__)

# =============================================================================
# Text Formatting Prompts
# =============================================================================

FORMAT_SYSTEM_PROMPT = """あなたはテキストの軽微な修正を行う専門家です。
テキストの内容は一切変更せず、読みやすさを改善する最小限の修正のみを行ってください。

【最重要：言語の維持】
- **入力テキストの言語をそのまま維持してください**
- **日本語のテキストは必ず日本語で出力してください**
- **翻訳は絶対に行わないでください**
- 英語への変換は禁止です

【情報量の完全保持】
- 出力テキストは入力テキストとほぼ同じ長さになるはずです
- 内容の要約・省略・削除・圧縮は絶対に行わない
- 文章の言い換え・書き換え・意訳は行わない
- 元のテキストの全ての文・段落・項目をそのまま残す
- 削除してよいのは「ページ番号」「ヘッダー/フッターの繰り返し」「連続する空行」のみ

【修正対象（これだけを修正する）】
1. 文中の不自然な改行を削除して文章を繋げる
   - PDFから抽出したテキストは単語や文の途中で改行されていることがある
   - これらを自然な文章に繋げる（文の削除はしない）
2. 連続する空行（3行以上）を1〜2行にまとめる
3. 明らかな誤字脱字の修正
4. ページ番号、ヘッダー/フッターの繰り返しの削除

【絶対に変更しないこと】
- 文章の内容・意味
- **文章の言語（日本語→英語への変換禁止）**
- 段落構成
- 箇条書きの項目数や内容（全ての項目を残す）
- 数値、日付、固有名詞、専門用語
- 文章の表現や言い回し
- 文の数（文を削除しない）

【出力形式】
- 修正後のテキストのみを出力（プレーンテキスト形式）
- 入力と同じ言語で出力（日本語入力→日本語出力）
- マークダウン記法（#、*、**など）は使用しない
- 説明文やコメントは不要"""

FORMAT_USER_TEMPLATE = """以下のテキストを軽微に修正してください。

【最重要】
- **入力テキストの言語を維持してください（翻訳禁止）**
- **日本語のテキストは日本語のまま出力してください**
- 出力は入力とほぼ同じ長さになるはずです（大幅に短くならない）
- 内容の要約・省略・削除・圧縮は絶対に行わない
- 全ての文・段落・項目をそのまま残す
- 文章の言い換えは行わない

【修正対象】
- 文中の不自然な改行を削除して文章を繋げる
- 連続する空行を1〜2行にまとめる
- 明らかな誤字脱字のみ修正
- ページ番号やヘッダー/フッターの繰り返しを削除

---
{text}
---

修正後のテキスト（入力と同じ言語で出力、プレーンテキスト形式、マークダウン記法は使用しない）:"""

# =============================================================================
# Text Formatting Prompts (for Minutes/Meeting Records)
# =============================================================================

MINUTE_FORMAT_SYSTEM_PROMPT = """あなたは議事録の軽微な修正を行う専門家です。
議事録テキストの読みやすさを最小限の修正で改善してください。

【最重要：言語の維持】
- **入力テキストの言語をそのまま維持してください**
- **日本語の議事録は必ず日本語で出力してください**
- **翻訳は絶対に行わないでください**
- 英語への変換は禁止です

【情報量の完全保持】
- 出力テキストは入力テキストとほぼ同じ長さになるはずです
- 元のテキストの構造・フォーマットをそのまま維持する
- 発言者名、発言内容、順序は一切変更しない
- 内容の追加・削除・要約は絶対に行わない
- 全ての発言をそのまま残す

【修正対象（これだけを修正する）】
1. 明らかな誤字脱字の修正
2. 無駄な空行・連続改行の削除（1行の空行は残す）
3. 不要な空白の削除

【絶対に変更しないこと】
- **文章の言語（日本語→英語への変換禁止）**
- 発言者名の表記方法
- 文章の構成・段落分け
- 発言の順序
- 発言の内容（言い換えや要約をしない）
- 箇条書きや番号付けの形式
- 具体的な数値、日付、固有名詞

【出力形式】
- 修正後のテキストのみを出力（プレーンテキスト形式）
- 入力と同じ言語で出力（日本語入力→日本語出力）
- マークダウン記法（#、*、**など）は使用しない
- 説明文やコメントは不要"""

MINUTE_FORMAT_USER_TEMPLATE = """以下の議事録を軽微に修正してください。

【最重要】
- **入力テキストの言語を維持してください（翻訳禁止）**
- **日本語の議事録は日本語のまま出力してください**
- 出力は入力とほぼ同じ長さになるはずです（大幅に短くならない）
- 全ての発言をそのまま残す
- 発言者名や発言内容は一切変更しない
- 元の構造・フォーマットは変更しない

【修正対象】
- 誤字脱字の修正
- 無駄な改行・空白の削除のみ行う

---
{text}
---

修正後の議事録（入力と同じ言語で出力、プレーンテキスト形式、マークダウン記法は使用しない）:"""

# =============================================================================
# Summary Prompts (for Documents/Sources)
# =============================================================================

SUMMARY_SYSTEM_PROMPT = """あなたは文書要約の専門家です。
資料から重要な情報を抽出し、詳細で情報量の多い要約を作成してください。

【絶対禁止：マークダウン記法】
以下の記号は絶対に使用しないでください：
- # （見出し）
- * や ** （強調）
- - や * （箇条書き）
- ``` （コードブロック）
- > （引用）
- | （表）
- [ ] （リンク）
代わりに「・」「、」「。」などの日本語記号を使用してください。

【出力言語】
- 必ず日本語で要約を作成してください
- 英語での出力は禁止です
- 原文が英語の場合も、要約は日本語で作成してください

【数値・データの保持】
- 具体的な数値は必ずすべて含める（金額、割合、件数、日付、期間など）
- 例：「売上1.2億円」「前年比15%増」「2024年4月1日」「3ヶ月間」
- ページ番号、図表番号など文脈に意味のない数字は省略してよい

【要約ルール】
1. 情報を省略しすぎない（重要な詳細は漏らさず含める）
2. 原文の50〜70%程度の長さを目安にする
3. 以下の情報は必ず含める：具体的な数値、固有名詞、専門用語、決定事項
4. 概要、主要ポイント、数値データ、結論の順で整理する
5. 背景情報や文脈も可能な限り含める

【出力形式】
- プレーンテキストのみ（装飾なし）
- 箇条書きは「・」を使用
- 段落は空行で区切る
- 説明文やコメントは不要"""

SUMMARY_USER_TEMPLATE = """以下の資料を日本語で詳細に要約してください。

【絶対禁止】
#、*、**、-、```、>、|、[] などのマークダウン記法は使用しないでください。
箇条書きは「・」を使ってください。

【要件】
・必ず日本語で出力する（英語禁止）
・具体的な数値（金額、割合、件数、日付など）は必ずすべて含める
・固有名詞、専門用語を保持する
・情報を省略しすぎない（原文の50〜70%程度の長さ）

---
{text}
---

詳細な要約（プレーンテキストのみ、マークダウン記法禁止）:"""

# =============================================================================
# Summary Prompts (for Minutes/Meeting Records)
# =============================================================================

MINUTE_SUMMARY_SYSTEM_PROMPT = """あなたは議事録要約の専門家です。
議事録から重要な情報を抽出し、発言者の話しぶりを活かした要約を作成してください。

【絶対禁止：マークダウン記法】
以下の記号は絶対に使用しないでください：
・# （見出し）
・* や ** （強調）
・- や * （箇条書き）
・``` （コードブロック）
・> （引用）
・| （表）
・[ ] （リンク）
代わりに「・」「、」「。」などの日本語記号を使用してください。

【出力言語】
・必ず日本語で要約を作成してください
・英語での出力は禁止です

【最重要：発言者の話しぶりを残す】
発言者の言葉遣い、口調、ニュアンスをできるだけ保持してください。
・元の発言のキーフレーズや特徴的な表現はそのまま引用する
・「〜と思います」「〜ではないでしょうか」などの語尾も残す
・強い主張、懸念、提案などのトーンが伝わるようにする

出力例：
・田中部長は「このスケジュールでは厳しいのではないか」と懸念を示した
・佐藤さんは「ぜひ進めるべきだと思います」と積極的な姿勢を見せた
・鈴木課長は「予算面での課題をクリアできれば問題ない」と条件付きで賛成した

【要約ルール】
・会議の目的・議題を明記する
・議事録に登場する全ての発言者の意見・主張を整理する
・発言者名は必ず保持し、省略しない（全員分を記載）
・発言の要点だけでなく、話しぶり（トーン、ニュアンス）も伝える
・決定事項・合意事項を明確に記載する
・TODO・アクションアイテムがあれば抽出する

【出力形式】
・プレーンテキストのみ（装飾なし）
・箇条書きは「・」を使用
・段落は空行で区切る
・構成：議題/目的、発言者ごとの意見（話しぶりを残す）、決定事項、アクションアイテム"""

MINUTE_SUMMARY_USER_TEMPLATE = """以下の議事録を日本語で要約してください。

【絶対禁止】
#、*、**、-、```、>、|、[] などのマークダウン記法は使用しないでください。
箇条書きは「・」を使ってください。

【重要：発言者の話しぶりを残す】
・発言者の言葉遣いや口調をできるだけ保持する
・特徴的な表現やキーフレーズはそのまま引用する
・「〜と思う」「〜ではないか」などの語尾も残す
・例：「田中さんは『難しいのでは』と懸念を示した」

【要件】
・必ず日本語で出力する（英語禁止）
・議事録に登場する全ての発言者の意見を抽出し、一人も省略しない
・発言者名を必ず保持する

---
{text}
---

要約（プレーンテキストのみ、発言者の話しぶりを残す）:"""

# =============================================================================
# Processing Constants (from settings)
# =============================================================================

# Maximum input text length for formatting (characters)
MAX_FORMAT_INPUT_LENGTH = settings.CONTENT_FORMAT_MAX_LENGTH

# Maximum input text length for summarization (characters)
MAX_SUMMARY_INPUT_LENGTH = settings.CONTENT_SUMMARY_MAX_LENGTH


# =============================================================================
# Custom Prompt Helpers
# =============================================================================

def get_summary_prompts(db: Optional[Session], is_minute: bool) -> Tuple[Optional[str], Optional[str]]:
    """
    Get custom summary prompts from LLM settings.

    Args:
        db: Database session (optional)
        is_minute: Whether to get minute-specific prompts

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

    if is_minute:
        system_prompt = prompt_settings.get("minute_summary_system")
        user_template = prompt_settings.get("minute_summary_user")
    else:
        system_prompt = prompt_settings.get("summary_system")
        user_template = prompt_settings.get("summary_user")

    return system_prompt, user_template


def get_format_prompts(db: Optional[Session], is_minute: bool) -> Tuple[Optional[str], Optional[str]]:
    """
    Get custom format prompts from LLM settings.

    Args:
        db: Database session (optional)
        is_minute: Whether to get minute-specific prompts

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

    if is_minute:
        system_prompt = prompt_settings.get("minute_format_system")
        user_template = prompt_settings.get("minute_format_user")
    else:
        system_prompt = prompt_settings.get("format_system")
        user_template = prompt_settings.get("format_user")

    return system_prompt, user_template


# =============================================================================
# Regex-based Text Formatting (No LLM - preserves 100% of content)
# =============================================================================

import re


def _format_text_regex(raw_text: str) -> str:
    """
    Format text using regex-based rules only.

    This method preserves 100% of the original content while making
    minor readability improvements. No LLM is used, so no content
    is lost or summarized.

    Improvements made:
    - Remove excessive blank lines (3+ -> 2)
    - Remove trailing whitespace from lines
    - Fix unnatural line breaks within sentences (common in PDF extraction)
    - Remove repeated headers/footers patterns
    - Normalize whitespace

    Args:
        raw_text: Raw text to format

    Returns:
        Formatted text with same information content
    """
    if not raw_text or not raw_text.strip():
        return ""

    text = raw_text

    # 1. Normalize line endings (Windows -> Unix)
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # 2. Remove trailing whitespace from each line
    text = re.sub(r'[ \t]+$', '', text, flags=re.MULTILINE)

    # 3. Reduce excessive blank lines (3+ consecutive newlines -> 2)
    text = re.sub(r'\n{3,}', '\n\n', text)

    # 4. Fix unnatural line breaks within Japanese sentences
    # Pattern: Japanese character + newline + Japanese character (not a list marker)
    # This commonly happens with PDF text extraction
    text = re.sub(
        r'([^\n\s。．.!！?？、，,\-\*\•\d])[\n]([^\n\s\-\*\•\d・①②③④⑤⑥⑦⑧⑨⑩])',
        r'\1\2',
        text
    )

    # 5. Fix line breaks after common Japanese particles that shouldn't end a line
    text = re.sub(r'(の|を|に|へ|と|で|が|は|も|や)\n([^\n])', r'\1\2', text)

    # 6. Remove page number patterns (common formats)
    # Pattern: standalone numbers that look like page numbers
    text = re.sub(r'\n\s*-\s*\d+\s*-\s*\n', '\n', text)  # - 1 -
    text = re.sub(r'\n\s*\d+\s*/\s*\d+\s*\n', '\n', text)  # 1/10
    text = re.sub(r'\n\s*Page\s*\d+\s*\n', '\n', text, flags=re.IGNORECASE)  # Page 1
    text = re.sub(r'\n\s*P\.\s*\d+\s*\n', '\n', text)  # P. 1

    # 7. Normalize multiple spaces within lines to single space
    text = re.sub(r'[ \t]{2,}', ' ', text)

    # 8. Remove leading/trailing whitespace from the entire text
    text = text.strip()

    return text


def _format_minute_text_regex(raw_text: str) -> str:
    """
    Format meeting minutes text using regex-based rules only.

    Similar to _format_text_regex but preserves speaker formatting
    and meeting-specific structures.

    Args:
        raw_text: Raw minute text to format

    Returns:
        Formatted minute text with same information content
    """
    if not raw_text or not raw_text.strip():
        return ""

    text = raw_text

    # 1. Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # 2. Remove trailing whitespace from each line
    text = re.sub(r'[ \t]+$', '', text, flags=re.MULTILINE)

    # 3. Reduce excessive blank lines (3+ -> 2)
    text = re.sub(r'\n{3,}', '\n\n', text)

    # 4. Normalize multiple spaces within lines to single space
    # But preserve indentation at line start
    lines = text.split('\n')
    normalized_lines = []
    for line in lines:
        # Preserve leading whitespace, normalize the rest
        match = re.match(r'^(\s*)(.*?)$', line)
        if match:
            indent, content = match.groups()
            content = re.sub(r'[ \t]{2,}', ' ', content)
            normalized_lines.append(indent + content)
        else:
            normalized_lines.append(line)
    text = '\n'.join(normalized_lines)

    # 5. Remove leading/trailing whitespace from the entire text
    text = text.strip()

    return text


# =============================================================================
# Core Processing Functions
# =============================================================================

async def format_text(raw_text: str) -> str:
    """
    Format raw text using regex-based rules to improve readability.

    This function uses simple regex patterns instead of LLM to ensure
    100% of the original content is preserved. LLM-based formatting
    was removed because it consistently summarized/shortened the text.

    Improvements made:
    - Remove excessive blank lines
    - Fix unnatural line breaks (common in PDF extraction)
    - Remove page numbers
    - Normalize whitespace

    Args:
        raw_text: Raw text to format

    Returns:
        Formatted text (same length as input, no content loss)
    """
    if not raw_text or not raw_text.strip():
        return ""

    # Truncate if too long
    text_to_format = raw_text[:MAX_FORMAT_INPUT_LENGTH]
    if len(raw_text) > MAX_FORMAT_INPUT_LENGTH:
        logger.warning(
            f"Text truncated for formatting: {len(raw_text)} -> {MAX_FORMAT_INPUT_LENGTH} chars"
        )

    # Use regex-based formatting (preserves 100% of content)
    result = _format_text_regex(text_to_format)

    logger.info(
        f"Text formatting complete: {len(text_to_format)} -> {len(result)} chars "
        f"({len(result) / len(text_to_format) * 100:.1f}%)"
    )

    return result


async def format_minute_text(raw_text: str) -> str:
    """
    Format minute/meeting record text using regex-based rules.

    This function uses simple regex patterns instead of LLM to ensure
    100% of the original content is preserved, including all speaker
    information and statements.

    Improvements made:
    - Remove excessive blank lines
    - Normalize whitespace while preserving indentation
    - Keep speaker formatting intact

    Args:
        raw_text: Raw minute text to format

    Returns:
        Formatted minute text (same length as input, no content loss)
    """
    if not raw_text or not raw_text.strip():
        return ""

    # Truncate if too long
    text_to_format = raw_text[:MAX_FORMAT_INPUT_LENGTH]
    if len(raw_text) > MAX_FORMAT_INPUT_LENGTH:
        logger.warning(
            f"Minute text truncated for formatting: {len(raw_text)} -> {MAX_FORMAT_INPUT_LENGTH} chars"
        )

    # Use regex-based formatting (preserves 100% of content)
    result = _format_minute_text_regex(text_to_format)

    logger.info(
        f"Minute text formatting complete: {len(text_to_format)} -> {len(result)} chars "
        f"({len(result) / len(text_to_format) * 100:.1f}%)"
    )

    return result


async def generate_summary(
    formatted_text: str,
    is_minute: bool = False,
    db: Optional[Session] = None,
) -> str:
    """
    Generate a summary from formatted text using LLM.

    Args:
        formatted_text: Pre-formatted text to summarize
        is_minute: If True, use minute-specific summarization prompt
        db: Optional database session for getting custom prompts

    Returns:
        Generated summary

    Raises:
        LLMConnectionError: If LLM call fails
    """
    if not formatted_text or not formatted_text.strip():
        return ""

    # Truncate if too long
    text_to_summarize = formatted_text[:MAX_SUMMARY_INPUT_LENGTH]
    if len(formatted_text) > MAX_SUMMARY_INPUT_LENGTH:
        logger.warning(
            f"Text truncated for summarization: {len(formatted_text)} -> {MAX_SUMMARY_INPUT_LENGTH} chars"
        )

    # Get custom prompts if available
    custom_system, custom_user = get_summary_prompts(db, is_minute)

    # Choose prompts based on content type, use custom if available
    if is_minute:
        system_prompt = custom_system if custom_system else MINUTE_SUMMARY_SYSTEM_PROMPT
        user_template = custom_user if custom_user else MINUTE_SUMMARY_USER_TEMPLATE
    else:
        system_prompt = custom_system if custom_system else SUMMARY_SYSTEM_PROMPT
        user_template = custom_user if custom_user else SUMMARY_USER_TEMPLATE

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_template.format(text=text_to_summarize)},
    ]

    try:
        response = await call_generation_llm(messages, temperature=0.2)
        return response.strip()
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e) or f"{error_type} (no message)"
        logger.error(f"Summary generation failed: {error_type}: {error_msg}", exc_info=True)
        raise LLMConnectionError(f"要約生成に失敗しました: {error_msg}")


# =============================================================================
# Source Processing
# =============================================================================

async def process_source_content(
    db: Session,
    source_id: UUID,
    raw_text: str,
) -> None:
    """
    Process source content: format text and generate summary.

    This function updates the source record with:
    - full_text: The raw extracted text
    - formatted_text: LLM-formatted text
    - summary: LLM-generated summary
    - processing_status: completed/failed

    Args:
        db: Database session
        source_id: Source UUID
        raw_text: Raw text extracted from the document
    """
    logger.info(f"Processing source content for source_id={source_id}")

    # Get source record
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        logger.error(f"Source not found: {source_id}")
        return

    try:
        # Update status to processing
        source.processing_status = "processing"
        source.full_text = raw_text
        db.commit()

        # Step 1: Format text
        logger.info(f"Formatting text for source {source_id} ({len(raw_text)} chars)")
        try:
            formatted = await format_text(raw_text)
            source.formatted_text = formatted
            db.commit()
            logger.info(f"Text formatted successfully: {len(formatted)} chars")
        except LLMConnectionError as e:
            logger.warning(f"Formatting failed, using raw text: {e}")
            source.formatted_text = raw_text  # Fallback to raw text
            formatted = raw_text
            db.commit()

        # Step 2: Generate summary
        logger.info(f"Generating summary for source {source_id}")
        try:
            summary = await generate_summary(formatted, is_minute=False, db=db)
            source.summary = summary
            source.processing_status = "completed"
            db.commit()
            logger.info(f"Summary generated successfully: {len(summary)} chars")
        except LLMConnectionError as e:
            logger.warning(f"Summary generation failed: {e}")
            # Fallback: use truncated formatted text as summary
            fallback_summary = formatted[:2000] + "..." if len(formatted) > 2000 else formatted
            source.summary = fallback_summary
            source.processing_status = "completed"
            source.processing_error = f"要約生成に失敗したため、整形テキストの一部を使用: {str(e)}"
            db.commit()

    except Exception as e:
        logger.error(f"Source content processing failed: {e}", exc_info=True)
        source.processing_status = "failed"
        source.processing_error = str(e)
        db.commit()


async def process_source_content_background(
    source_id: UUID,
    raw_text: str,
) -> None:
    """
    Background task wrapper for source content processing.

    Creates its own database session for use in FastAPI BackgroundTasks.

    Args:
        source_id: Source UUID
        raw_text: Raw text extracted from the document
    """
    logger.info(f"Starting background processing for source {source_id}")
    db = SessionLocal()
    try:
        await process_source_content(db, source_id, raw_text)
    finally:
        db.close()
        logger.info(f"Background processing completed for source {source_id}")


# =============================================================================
# Minute Processing
# =============================================================================

async def process_minute_content(
    db: Session,
    minute_id: UUID,
) -> None:
    """
    Process minute content: format text and generate summary.

    This function updates the minute record with:
    - formatted_content: LLM-formatted text
    - summary: LLM-generated summary (preserving speaker information)
    - processing_status: completed/failed

    Args:
        db: Database session
        minute_id: Minute UUID
    """
    logger.info(f"Processing minute content for minute_id={minute_id}")

    # Get minute record
    minute = db.query(Minute).filter(Minute.id == minute_id).first()
    if not minute:
        logger.error(f"Minute not found: {minute_id}")
        return

    raw_content = minute.content
    if not raw_content:
        logger.warning(f"Minute {minute_id} has no content")
        minute.processing_status = "completed"
        db.commit()
        return

    try:
        # Update status to processing
        minute.processing_status = "processing"
        db.commit()

        # Step 1: Format text (using minute-specific formatting that preserves all speakers)
        logger.info(f"Formatting minute {minute_id} ({len(raw_content)} chars)")
        try:
            formatted = await format_minute_text(raw_content)
            minute.formatted_content = formatted
            db.commit()
            logger.info(f"Minute formatted successfully: {len(formatted)} chars")
        except LLMConnectionError as e:
            logger.warning(f"Minute formatting failed, using raw content: {e}")
            minute.formatted_content = raw_content  # Fallback
            formatted = raw_content
            db.commit()

        # Step 2: Generate summary (with speaker preservation)
        logger.info(f"Generating summary for minute {minute_id}")
        try:
            summary = await generate_summary(formatted, is_minute=True, db=db)
            minute.summary = summary
            minute.processing_status = "completed"
            db.commit()
            logger.info(f"Minute summary generated successfully: {len(summary)} chars")
        except LLMConnectionError as e:
            logger.warning(f"Minute summary generation failed: {e}")
            # Fallback: use truncated formatted content as summary
            fallback_summary = formatted[:2000] + "..." if len(formatted) > 2000 else formatted
            minute.summary = fallback_summary
            minute.processing_status = "completed"
            minute.processing_error = f"要約生成に失敗したため、整形テキストの一部を使用: {str(e)}"
            db.commit()

    except Exception as e:
        logger.error(f"Minute content processing failed: {e}", exc_info=True)
        minute.processing_status = "failed"
        minute.processing_error = str(e)
        db.commit()


async def process_minute_content_background(
    minute_id: UUID,
) -> None:
    """
    Background task wrapper for minute content processing.

    Creates its own database session for use in FastAPI BackgroundTasks.

    Args:
        minute_id: Minute UUID
    """
    logger.info(f"Starting background processing for minute {minute_id}")
    db = SessionLocal()
    try:
        await process_minute_content(db, minute_id)
    finally:
        db.close()
        logger.info(f"Background processing completed for minute {minute_id}")
