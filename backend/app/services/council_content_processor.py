"""
Council Content Processor service for processing council agenda item materials and minutes.

This module handles:
1. URL content fetching for materials and minutes
2. Text formatting using regex (preserves 100% content)
3. LLM-based summary generation (preserves key information)
4. Chunk creation with embeddings for RAG
5. Background task processing
"""
import logging
import re
import uuid
from typing import Optional, Literal, List
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.council_agenda_item import CouncilAgendaItem
from app.models.council_agenda_chunk import CouncilAgendaChunk
from app.models.council_agenda_material import CouncilAgendaMaterial
from app.models.llm_settings import LLMSettings
from app.services.url_content_fetcher import fetch_url_with_retry, URLContentFetchError
from app.services.llm_client import call_generation_llm
from app.services.embedding import get_embedding_client
from app.core.exceptions import LLMConnectionError
from app.core.config import settings

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

# Maximum text length for processing
MAX_TEXT_LENGTH = 100000  # 100K characters

# Chunk size for RAG embedding
CHUNK_SIZE = 1000  # characters per chunk
CHUNK_OVERLAP = 200  # overlap between chunks

# =============================================================================
# Summary Prompts for Council Materials
# =============================================================================

COUNCIL_SUMMARY_SYSTEM_PROMPT = """あなたは日本語専用のアシスタントです。全ての回答は日本語のみで行ってください。英語での回答は絶対に禁止です。

あなたは審議会資料の要約を作成する専門家です。
電力・エネルギー関連の審議会資料から重要な情報を抽出し、詳細で情報量の多い要約を作成してください。

【最重要：出力言語は日本語のみ】
・全ての出力は必ず日本語で記述すること
・英語での出力は一切禁止（固有名詞・専門用語の英語表記は可）
・「Summary:」「Overview:」などの英語見出しは禁止
・「The」「This」「In」などで始まる英語文は禁止

【絶対禁止：マークダウン記法】
以下の記号は絶対に使用しないでください：
・# （見出し）
・* や ** （強調）
・- （リスト）
・``` （コードブロック）
代わりに「・」「、」「。」などの日本語記号を使用してください。

【情報量の維持（最重要）】
・原文の70〜80%程度の情報量を維持する
・数値データは必ずすべて含める（目標値、実績値、割合、金額、日付など）
・固有名詞、専門用語、法令名、制度名は必ず保持する
・議論の経緯や背景情報も省略しない

【必ず含める情報】
1. 議題・検討事項の概要
2. 現状・背景の説明（数値データ含む）
3. 課題・論点の整理
4. 委員の意見・発言のポイント
5. 結論・決定事項・今後の方向性
6. スケジュール・期限があれば記載

【出力形式】
・プレーンテキストのみ（装飾なし）
・箇条書きは「・」を使用
・段落は空行で区切る
・構造化して読みやすく整理する"""

COUNCIL_SUMMARY_USER_TEMPLATE = """以下の審議会資料を日本語で詳細に要約してください。

【最重要：日本語のみで出力】
・全ての文章を日本語で記述すること
・英語の見出し（Summary:, Overview:等）は禁止
・英語で始まる文章は禁止

【絶対禁止：マークダウン記法】
#、*、**、-、```、>、|、[] などのマークダウン記法は使用しないでください。
箇条書きは「・」を使ってください。

【要件】
・原文の70〜80%程度の情報量を維持する
・具体的な数値（目標値、実績値、割合、金額、日付など）は必ずすべて含める
・固有名詞、専門用語、法令名、制度名を保持する
・議論の経緯や背景情報も省略しない

---
{text}
---

日本語での詳細な要約（プレーンテキストのみ、マークダウン記法禁止、英語禁止）:"""

# =============================================================================
# Summary Prompts for Council Minutes
# =============================================================================

COUNCIL_MINUTES_SUMMARY_SYSTEM_PROMPT = """あなたは日本語専用のアシスタントです。全ての回答は日本語のみで行ってください。英語での回答は絶対に禁止です。

あなたは審議会議事録の要約を作成する専門家です。
電力・エネルギー関連の審議会議事録から重要な情報を抽出し、発言者の話しぶりを活かした要約を作成してください。

【最重要：出力言語は日本語のみ】
・全ての出力は必ず日本語で記述すること
・英語での出力は一切禁止（固有名詞・専門用語の英語表記は可）
・「Summary:」「Minutes:」などの英語見出しは禁止
・「The」「This」「In」などで始まる英語文は禁止

【絶対禁止：マークダウン記法】
以下の記号は絶対に使用しないでください：
・# （見出し）
・* や ** （強調）
・- （リスト）
・``` （コードブロック）
代わりに「・」「、」「。」などの日本語記号を使用してください。

【情報量の維持（最重要）】
・原文の70〜80%程度の情報量を維持する
・発言者名と発言内容は必ず紐付けて記載する
・数値データ、固有名詞、専門用語は必ず保持する

【発言者の話しぶりを残す（重要）】
・発言者の言葉遣い、口調、ニュアンスをできるだけ保持する
・特徴的な表現やキーフレーズはそのまま引用する
・「〜と思います」「〜ではないでしょうか」などの語尾も残す
・賛成/反対/懸念/提案などの立場が明確に伝わるようにする

例：
・○○委員は「このままでは目標達成は難しいのではないか」と懸念を示した
・△△委員は「再エネ比率の引き上げは必須だと考える」と主張した

【必ず含める情報】
1. 会議の議題・目的
2. 出席者（主要な発言者）
3. 各発言者の意見・主張（話しぶりを残す）
4. 議論のポイント・論点
5. 決定事項・合意事項
6. 今後の予定・アクションアイテム

【出力形式】
・プレーンテキストのみ（装飾なし）
・箇条書きは「・」を使用
・段落は空行で区切る"""

COUNCIL_MINUTES_SUMMARY_USER_TEMPLATE = """以下の審議会議事録を日本語で要約してください。

【最重要：日本語のみで出力】
・全ての文章を日本語で記述すること
・英語の見出し（Summary:, Minutes:等）は禁止
・英語で始まる文章は禁止

【絶対禁止：マークダウン記法】
#、*、**、-、```、>、|、[] などのマークダウン記法は使用しないでください。
箇条書きは「・」を使ってください。

【重要：発言者の話しぶりを残す】
・発言者の言葉遣いや口調をできるだけ保持する
・特徴的な表現やキーフレーズはそのまま引用する
・例：「○○委員は『厳しいのでは』と懸念を示した」

【要件】
・原文の70〜80%程度の情報量を維持する
・議事録に登場する全ての発言者の意見を抽出する
・発言者名を必ず保持する

---
{text}
---

日本語での要約（プレーンテキストのみ、発言者の話しぶりを残す、英語禁止）:"""


# =============================================================================
# Prompt Helpers
# =============================================================================

def get_custom_prompts(db: Session, content_type: Literal["materials", "minutes"]) -> tuple[Optional[str], Optional[str]]:
    """
    Get custom prompts from LLM settings.

    Args:
        db: Database session
        content_type: Type of content ("materials" or "minutes")

    Returns:
        Tuple of (system_prompt, user_template), both can be None if using defaults
    """
    # Get system-level LLM settings (user_id is NULL)
    settings_record = db.query(LLMSettings).filter(LLMSettings.user_id.is_(None)).first()

    if not settings_record or not settings_record.prompt_settings:
        return None, None

    prompt_settings = settings_record.prompt_settings

    if content_type == "minutes":
        system_prompt = prompt_settings.get("council_minutes_system")
        user_template = prompt_settings.get("council_minutes_user")
    else:
        system_prompt = prompt_settings.get("council_materials_system")
        user_template = prompt_settings.get("council_materials_user")

    return system_prompt, user_template


# =============================================================================
# Text Processing Functions
# =============================================================================

def _format_text_regex(raw_text: str) -> str:
    """
    Format text using regex-based rules only.
    Preserves 100% of the original content while improving readability.
    """
    if not raw_text or not raw_text.strip():
        return ""

    text = raw_text

    # Normalize line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Remove trailing whitespace from each line
    text = re.sub(r'[ \t]+$', '', text, flags=re.MULTILINE)

    # Reduce excessive blank lines (3+ -> 2)
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Fix unnatural line breaks within Japanese sentences
    text = re.sub(
        r'([^\n\s。．.!！?？、，,\-\*\•\d])[\n]([^\n\s\-\*\•\d・①②③④⑤⑥⑦⑧⑨⑩])',
        r'\1\2',
        text
    )

    # Fix line breaks after common Japanese particles
    text = re.sub(r'(の|を|に|へ|と|で|が|は|も|や)\n([^\n])', r'\1\2', text)

    # Remove page number patterns
    text = re.sub(r'\n\s*-\s*\d+\s*-\s*\n', '\n', text)
    text = re.sub(r'\n\s*\d+\s*/\s*\d+\s*\n', '\n', text)
    text = re.sub(r'\n\s*Page\s*\d+\s*\n', '\n', text, flags=re.IGNORECASE)

    # Normalize multiple spaces within lines
    text = re.sub(r'[ \t]{2,}', ' ', text)

    return text.strip()


def _split_into_chunks(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Split text into overlapping chunks for RAG embedding.

    Args:
        text: Text to split
        chunk_size: Maximum size of each chunk
        overlap: Overlap between consecutive chunks

    Returns:
        List of text chunks
    """
    if not text:
        return []

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size

        # If not at the end, try to break at a sentence boundary
        if end < text_length:
            # Look for sentence endings (。！？) within a window
            search_start = max(end - 100, start)
            search_text = text[search_start:end]

            # Find the last sentence boundary
            for pattern in ['。', '！', '？', '.\n', '\n\n']:
                last_idx = search_text.rfind(pattern)
                if last_idx != -1:
                    end = search_start + last_idx + len(pattern)
                    break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Move start position with overlap
        start = end - overlap if end < text_length else text_length

    return chunks


# =============================================================================
# Core Processing Functions
# =============================================================================

async def generate_council_summary(
    text: str,
    content_type: Literal["materials", "minutes"],
    custom_system_prompt: Optional[str] = None,
    custom_user_template: Optional[str] = None,
) -> str:
    """
    Generate a summary for council materials or minutes.

    Args:
        text: Text to summarize
        content_type: Type of content ("materials" or "minutes")
        custom_system_prompt: Optional custom system prompt (None = use default)
        custom_user_template: Optional custom user template (None = use default)

    Returns:
        Generated summary

    Raises:
        LLMConnectionError: If LLM call fails
    """
    if not text or not text.strip():
        return ""

    # Truncate if too long
    text_to_summarize = text[:MAX_TEXT_LENGTH]
    if len(text) > MAX_TEXT_LENGTH:
        logger.warning(f"Text truncated for summarization: {len(text)} -> {MAX_TEXT_LENGTH}")

    # Choose prompts based on content type, use custom if provided
    if content_type == "minutes":
        system_prompt = custom_system_prompt if custom_system_prompt else COUNCIL_MINUTES_SUMMARY_SYSTEM_PROMPT
        user_template = custom_user_template if custom_user_template else COUNCIL_MINUTES_SUMMARY_USER_TEMPLATE
    else:
        system_prompt = custom_system_prompt if custom_system_prompt else COUNCIL_SUMMARY_SYSTEM_PROMPT
        user_template = custom_user_template if custom_user_template else COUNCIL_SUMMARY_USER_TEMPLATE

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_template.format(text=text_to_summarize)},
    ]

    try:
        response = await call_generation_llm(messages, temperature=0.2)
        return response.strip()
    except Exception as e:
        error_msg = str(e) or type(e).__name__
        logger.error(f"Council summary generation failed: {error_msg}", exc_info=True)
        raise LLMConnectionError(f"Summary generation failed: {error_msg}")


async def create_agenda_chunks(
    db: Session,
    agenda_id: UUID,
    text: str,
    chunk_type: Literal["materials", "minutes"],
    material_id: Optional[UUID] = None,
) -> int:
    """
    Create text chunks with embeddings for a council agenda item.

    Args:
        db: Database session
        agenda_id: Agenda item UUID
        text: Text to chunk
        chunk_type: Type of content
        material_id: Optional material UUID for materials chunks

    Returns:
        Number of chunks created
    """
    if not text or not text.strip():
        return 0

    # Delete existing chunks of this type (and material_id if provided)
    delete_query = db.query(CouncilAgendaChunk).filter(
        CouncilAgendaChunk.agenda_id == agenda_id,
        CouncilAgendaChunk.chunk_type == chunk_type,
    )
    if material_id:
        delete_query = delete_query.filter(CouncilAgendaChunk.material_id == material_id)
    delete_query.delete()

    # Split into chunks
    chunks = _split_into_chunks(text)
    if not chunks:
        return 0

    # Generate embeddings
    embedding_client = get_embedding_client()
    try:
        embeddings = await embedding_client.embed(chunks)
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}", exc_info=True)
        embeddings = [None] * len(chunks)

    # Create chunk records
    for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
        chunk = CouncilAgendaChunk(
            id=uuid.uuid4(),
            agenda_id=agenda_id,
            material_id=material_id,
            chunk_type=chunk_type,
            chunk_index=i,
            content=chunk_text,
            embedding=embedding,
        )
        db.add(chunk)

    db.commit()
    log_msg = f"Created {len(chunks)} {chunk_type} chunks for agenda {agenda_id}"
    if material_id:
        log_msg += f" (material {material_id})"
    logger.info(log_msg)
    return len(chunks)


# =============================================================================
# Agenda Content Processing
# =============================================================================

async def process_agenda_materials(
    db: Session,
    agenda_id: UUID,
) -> None:
    """
    Process materials URL for a council agenda item.

    Steps:
    1. Fetch content from materials_url
    2. Format text (regex-based)
    3. Generate summary (LLM)
    4. Create chunks with embeddings

    Args:
        db: Database session
        agenda_id: Agenda item UUID
    """
    agenda = db.query(CouncilAgendaItem).filter(CouncilAgendaItem.id == agenda_id).first()
    if not agenda:
        logger.error(f"Agenda item not found: {agenda_id}")
        return

    if not agenda.materials_url:
        logger.info(f"No materials URL for agenda {agenda_id}")
        return

    try:
        agenda.materials_processing_status = "processing"
        db.commit()

        # Step 1: Fetch content
        logger.info(f"Fetching materials from: {agenda.materials_url}")
        text, content_type = await fetch_url_with_retry(agenda.materials_url)
        logger.info(f"Fetched {len(text)} chars ({content_type})")

        # Step 2: Format text
        formatted_text = _format_text_regex(text)
        agenda.materials_text = formatted_text
        db.commit()

        # Step 3: Generate summary
        logger.info(f"Generating materials summary for agenda {agenda_id}")
        try:
            # Get custom prompts from settings
            custom_system, custom_user = get_custom_prompts(db, "materials")
            summary = await generate_council_summary(
                formatted_text, "materials",
                custom_system_prompt=custom_system,
                custom_user_template=custom_user
            )
            agenda.materials_summary = summary
            logger.info(f"Summary generated: {len(summary)} chars")
        except LLMConnectionError as e:
            logger.warning(f"Summary generation failed: {e}")
            agenda.materials_summary = formatted_text[:3000] + "..." if len(formatted_text) > 3000 else formatted_text
            agenda.processing_error = f"Materials summary generation failed: {str(e)}"

        # Step 4: Create chunks
        await create_agenda_chunks(db, agenda_id, formatted_text, "materials")

        agenda.materials_processing_status = "completed"
        db.commit()
        logger.info(f"Materials processing completed for agenda {agenda_id}")

    except URLContentFetchError as e:
        logger.error(f"Materials fetch failed: {e}")
        agenda.materials_processing_status = "failed"
        agenda.processing_error = f"Materials fetch failed: {str(e)}"
        db.commit()
    except Exception as e:
        logger.error(f"Materials processing failed: {e}", exc_info=True)
        agenda.materials_processing_status = "failed"
        agenda.processing_error = f"Materials processing failed: {str(e)}"
        db.commit()


async def process_agenda_minutes(
    db: Session,
    agenda_id: UUID,
) -> None:
    """
    Process minutes URL for a council agenda item.

    Steps:
    1. Fetch content from minutes_url
    2. Format text (regex-based)
    3. Generate summary (LLM)
    4. Create chunks with embeddings

    Args:
        db: Database session
        agenda_id: Agenda item UUID
    """
    agenda = db.query(CouncilAgendaItem).filter(CouncilAgendaItem.id == agenda_id).first()
    if not agenda:
        logger.error(f"Agenda item not found: {agenda_id}")
        return

    if not agenda.minutes_url:
        logger.info(f"No minutes URL for agenda {agenda_id}")
        return

    try:
        agenda.minutes_processing_status = "processing"
        db.commit()

        # Step 1: Fetch content
        logger.info(f"Fetching minutes from: {agenda.minutes_url}")
        text, content_type = await fetch_url_with_retry(agenda.minutes_url)
        logger.info(f"Fetched {len(text)} chars ({content_type})")

        # Step 2: Format text
        formatted_text = _format_text_regex(text)
        agenda.minutes_text = formatted_text
        db.commit()

        # Step 3: Generate summary
        logger.info(f"Generating minutes summary for agenda {agenda_id}")
        try:
            # Get custom prompts from settings
            custom_system, custom_user = get_custom_prompts(db, "minutes")
            summary = await generate_council_summary(
                formatted_text, "minutes",
                custom_system_prompt=custom_system,
                custom_user_template=custom_user
            )
            agenda.minutes_summary = summary
            logger.info(f"Summary generated: {len(summary)} chars")
        except LLMConnectionError as e:
            logger.warning(f"Summary generation failed: {e}")
            agenda.minutes_summary = formatted_text[:3000] + "..." if len(formatted_text) > 3000 else formatted_text
            agenda.processing_error = (agenda.processing_error or "") + f" Minutes summary generation failed: {str(e)}"

        # Step 4: Create chunks
        await create_agenda_chunks(db, agenda_id, formatted_text, "minutes")

        agenda.minutes_processing_status = "completed"
        db.commit()
        logger.info(f"Minutes processing completed for agenda {agenda_id}")

    except URLContentFetchError as e:
        logger.error(f"Minutes fetch failed: {e}")
        agenda.minutes_processing_status = "failed"
        agenda.processing_error = (agenda.processing_error or "") + f" Minutes fetch failed: {str(e)}"
        db.commit()
    except Exception as e:
        logger.error(f"Minutes processing failed: {e}", exc_info=True)
        agenda.minutes_processing_status = "failed"
        agenda.processing_error = (agenda.processing_error or "") + f" Minutes processing failed: {str(e)}"
        db.commit()


async def process_single_material(
    db: Session,
    material: CouncilAgendaMaterial,
) -> None:
    """
    Process a single material for a council agenda item.

    Steps:
    1. Fetch content from material URL
    2. Format text (regex-based)
    3. Generate summary (LLM)
    4. Create chunks with embeddings

    Args:
        db: Database session
        material: Material to process
    """
    if not material.url:
        logger.info(f"No URL for material {material.id}")
        return

    try:
        material.processing_status = "processing"
        db.commit()

        # Step 1: Fetch content
        logger.info(f"Fetching material from: {material.url}")
        text, content_type = await fetch_url_with_retry(material.url)
        logger.info(f"Fetched {len(text)} chars ({content_type})")

        # Step 2: Format text
        formatted_text = _format_text_regex(text)
        material.text = formatted_text
        db.commit()

        # Step 3: Generate summary
        logger.info(f"Generating summary for material {material.id}")
        try:
            # Get custom prompts from settings
            custom_system, custom_user = get_custom_prompts(db, "materials")
            summary = await generate_council_summary(
                formatted_text, "materials",
                custom_system_prompt=custom_system,
                custom_user_template=custom_user
            )
            material.summary = summary
            logger.info(f"Summary generated: {len(summary)} chars")
        except LLMConnectionError as e:
            logger.warning(f"Summary generation failed: {e}")
            material.summary = formatted_text[:3000] + "..." if len(formatted_text) > 3000 else formatted_text
            material.processing_error = f"Summary generation failed: {str(e)}"

        # Step 4: Create chunks
        await create_agenda_chunks(db, material.agenda_id, formatted_text, "materials", material.id)

        material.processing_status = "completed"
        db.commit()
        logger.info(f"Material processing completed for material {material.id}")

    except URLContentFetchError as e:
        logger.error(f"Material fetch failed: {e}")
        material.processing_status = "failed"
        material.processing_error = f"Content fetch failed: {str(e)}"
        db.commit()
    except Exception as e:
        logger.error(f"Material processing failed: {e}", exc_info=True)
        material.processing_status = "failed"
        material.processing_error = f"Processing failed: {str(e)}"
        db.commit()


async def process_agenda_materials_new(
    db: Session,
    agenda_id: UUID,
) -> None:
    """
    Process all materials in the new CouncilAgendaMaterial table for an agenda item.

    Args:
        db: Database session
        agenda_id: Agenda item UUID
    """
    agenda = db.query(CouncilAgendaItem).filter(CouncilAgendaItem.id == agenda_id).first()
    if not agenda:
        logger.error(f"Agenda item not found: {agenda_id}")
        return

    if not agenda.materials:
        logger.info(f"No materials for agenda {agenda_id}")
        return

    logger.info(f"Processing {len(agenda.materials)} materials for agenda {agenda_id}")
    for material in agenda.materials:
        if material.processing_status == "pending":
            await process_single_material(db, material)


async def process_agenda_content(
    db: Session,
    agenda_id: UUID,
) -> None:
    """
    Process both materials and minutes for a council agenda item.

    Processes:
    1. Legacy materials_url on agenda item
    2. New materials from CouncilAgendaMaterial table
    3. Minutes

    Args:
        db: Database session
        agenda_id: Agenda item UUID
    """
    # Process legacy materials_url
    await process_agenda_materials(db, agenda_id)
    # Process new materials from materials table
    await process_agenda_materials_new(db, agenda_id)
    # Process minutes
    await process_agenda_minutes(db, agenda_id)


# =============================================================================
# Background Task Wrappers
# =============================================================================

async def process_agenda_content_background(agenda_id: UUID) -> None:
    """
    Background task wrapper for processing agenda content.

    Creates its own database session for use in FastAPI BackgroundTasks.
    """
    logger.info(f"Starting background processing for agenda {agenda_id}")
    db = SessionLocal()
    try:
        await process_agenda_content(db, agenda_id)
    finally:
        db.close()
        logger.info(f"Background processing completed for agenda {agenda_id}")


async def process_agenda_materials_background(agenda_id: UUID) -> None:
    """Background task wrapper for processing materials only."""
    logger.info(f"Starting background materials processing for agenda {agenda_id}")
    db = SessionLocal()
    try:
        await process_agenda_materials(db, agenda_id)
    finally:
        db.close()
        logger.info(f"Background materials processing completed for agenda {agenda_id}")


async def process_agenda_minutes_background(agenda_id: UUID) -> None:
    """Background task wrapper for processing minutes only."""
    logger.info(f"Starting background minutes processing for agenda {agenda_id}")
    db = SessionLocal()
    try:
        await process_agenda_minutes(db, agenda_id)
    finally:
        db.close()
        logger.info(f"Background minutes processing completed for agenda {agenda_id}")


async def regenerate_agenda_summary_background(
    agenda_id: UUID,
    content_type: Literal["materials", "minutes", "both"],
) -> None:
    """
    Background task wrapper for regenerating summaries.

    If text content doesn't exist but URL does, re-fetches content first.

    Args:
        agenda_id: Agenda item UUID
        content_type: Which summaries to regenerate
    """
    logger.info(f"Starting summary regeneration for agenda {agenda_id} ({content_type})")
    db = SessionLocal()
    try:
        agenda = db.query(CouncilAgendaItem).filter(CouncilAgendaItem.id == agenda_id).first()
        if not agenda:
            logger.error(f"Agenda item not found: {agenda_id}")
            return

        # Process materials
        if content_type in ("materials", "both") and agenda.materials_url:
            if agenda.materials_text:
                # Text exists, just regenerate summary
                agenda.materials_processing_status = "processing"
                db.commit()
                try:
                    # Get custom prompts from settings
                    custom_system, custom_user = get_custom_prompts(db, "materials")
                    summary = await generate_council_summary(
                        agenda.materials_text, "materials",
                        custom_system_prompt=custom_system,
                        custom_user_template=custom_user
                    )
                    agenda.materials_summary = summary
                    agenda.materials_processing_status = "completed"
                    logger.info(f"Materials summary regenerated: {len(summary)} chars")
                except Exception as e:
                    agenda.materials_processing_status = "failed"
                    agenda.processing_error = f"Materials summary regeneration failed: {str(e)}"
                    logger.error(f"Materials summary regeneration failed: {e}")
                db.commit()
            else:
                # Text doesn't exist, need to re-fetch content first
                logger.info(f"Materials text missing, re-fetching from URL")
                await process_agenda_materials(db, agenda_id)

        # Process minutes
        if content_type in ("minutes", "both") and agenda.minutes_url:
            # Refresh agenda to get latest state
            db.refresh(agenda)
            if agenda.minutes_text:
                # Text exists, just regenerate summary
                agenda.minutes_processing_status = "processing"
                db.commit()
                try:
                    # Get custom prompts from settings
                    custom_system, custom_user = get_custom_prompts(db, "minutes")
                    summary = await generate_council_summary(
                        agenda.minutes_text, "minutes",
                        custom_system_prompt=custom_system,
                        custom_user_template=custom_user
                    )
                    agenda.minutes_summary = summary
                    agenda.minutes_processing_status = "completed"
                    logger.info(f"Minutes summary regenerated: {len(summary)} chars")
                except Exception as e:
                    agenda.minutes_processing_status = "failed"
                    agenda.processing_error = (agenda.processing_error or "") + f" Minutes summary regeneration failed: {str(e)}"
                    logger.error(f"Minutes summary regeneration failed: {e}")
                db.commit()
            else:
                # Text doesn't exist, need to re-fetch content first
                logger.info(f"Minutes text missing, re-fetching from URL")
                await process_agenda_minutes(db, agenda_id)

    finally:
        db.close()
        logger.info(f"Summary regeneration completed for agenda {agenda_id}")
