"""
Chat Background Processor Service.

This module handles asynchronous chat message processing:
- Creates pending messages immediately for quick response
- Processes LLM generation in background
- Updates message status when complete or failed
"""

import asyncio
import json
import logging
import threading
from typing import List, Optional
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models.chat_session import ChatSession
from app.models.message import Message
from app.models.source import Source
from app.services.embedding import embed_texts
from app.services.llm_client import call_llm
from app.services.rag_utils import (
    get_conversation_history_generic,
    update_session_timestamp,
)

logger = logging.getLogger(__name__)


# Message status constants
STATUS_PENDING = "pending"
STATUS_GENERATING = "generating"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"


def get_conversation_history(
    db: Session,
    session_id: UUID,
    max_messages: int = None,
    max_chars: int = None,
) -> List[dict]:
    """Retrieve conversation history from a session for LLM context."""
    return get_conversation_history_generic(
        db=db,
        session_id=session_id,
        message_model=Message,
        max_messages=max_messages,
        max_chars=max_chars,
    )


async def process_chat_message_async(
    message_id: UUID,
    db_url: str,
    notebook_id: UUID,
    session_id: Optional[UUID],
    question: str,
    source_ids: Optional[List[str]],
    use_rag: bool,
    use_formatted_text: bool,
):
    """
    Process a chat message asynchronously.

    This function:
    1. Updates message status to 'generating'
    2. Retrieves conversation history
    3. Generates answer using RAG or free mode
    4. Updates message with answer and status 'completed'
    5. On error, updates status to 'failed' with error message

    Args:
        message_id: UUID of the assistant message to update
        db_url: Database connection URL
        notebook_id: Notebook UUID
        session_id: Optional session UUID
        question: User's question
        source_ids: Optional list of source IDs for RAG
        use_rag: Whether to use RAG mode
        use_formatted_text: Whether to use full text mode
    """
    # Create a new session for background task
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Get the message and update status to generating
        message = db.query(Message).filter(Message.id == message_id).first()
        if not message:
            logger.error(f"Message not found: {message_id}")
            return

        message.status = STATUS_GENERATING
        db.commit()

        logger.info(f"Processing chat message: {message_id}")

        # Get conversation history
        conversation_history = []
        if session_id:
            conversation_history = get_conversation_history(db, session_id)
            logger.debug(f"Retrieved {len(conversation_history)} messages from history")

        # Determine mode and process
        answer = ""
        source_refs = []

        if use_formatted_text:
            # Formatted Text Mode
            answer, source_refs = await _process_formatted_text_mode(
                db, notebook_id, source_ids, question, conversation_history
            )
        elif use_rag:
            # RAG Mode
            answer, source_refs = await _process_rag_mode(
                db, notebook_id, source_ids, question, conversation_history
            )
        else:
            # Free Mode
            answer = await _process_free_mode(question, conversation_history)
            source_refs = []

        # Update message with answer
        message.content = answer
        message.source_refs = json.dumps(source_refs)
        message.status = STATUS_COMPLETED
        db.commit()

        # Update session timestamp
        if session_id:
            update_session_timestamp(db, session_id, ChatSession)

        logger.info(f"Chat message completed: {message_id}")

    except Exception as e:
        logger.error(f"Chat processing failed for {message_id}: {e}")
        try:
            message = db.query(Message).filter(Message.id == message_id).first()
            if message:
                message.status = STATUS_FAILED
                message.error_message = str(e)
                message.content = f"エラーが発生しました: {str(e)}"
                db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update error status: {db_error}")

    finally:
        db.close()


async def _process_formatted_text_mode(
    db: Session,
    notebook_id: UUID,
    source_ids: Optional[List[str]],
    question: str,
    conversation_history: List[dict],
) -> tuple[str, List[str]]:
    """Process using full formatted text from sources."""
    # Get source IDs
    if source_ids:
        uuid_source_ids = [UUID(sid) for sid in source_ids]
    else:
        rows = db.execute(f"SELECT id FROM sources WHERE notebook_id = '{notebook_id}'")
        uuid_source_ids = [row[0] for row in rows]

    if not uuid_source_ids:
        return "このNotebookにはソースが登録されていません。", []

    # Get sources
    sources = db.query(Source).filter(Source.id.in_(uuid_source_ids)).all()

    contexts = []
    source_refs = []

    for source in sources:
        text_content = source.formatted_text or source.full_text
        if text_content:
            contexts.append(f"【{source.title}】\n{text_content}")
            source_refs.append(source.title)

    if not contexts:
        return "選択されたソースにはテキストデータがありません。", []

    context_text = "\n\n---\n\n".join(contexts)
    max_context_chars = 30000
    if len(context_text) > max_context_chars:
        context_text = (
            context_text[:max_context_chars] + "\n\n[...テキストが長いため一部省略...]"
        )

    system_prompt = (
        "あなたは社内資料の内容に基づいて回答するアシスタントです。\n"
        "以下のルールに従ってください：\n"
        "1. 提供された資料の全文を参照して、詳細かつ正確に回答してください\n"
        "2. 資料にない情報については推測せず「分かりません」と答えてください\n"
        "3. 会話の文脈を考慮して、一貫性のある対話を心がけてください\n"
        "4. 資料の内容を引用・要約する際は、元の情報を正確に伝えてください\n"
        "5. 回答はプレーンテキストで出力してください。マークダウン記法は使用しないでください\n"
        "6. 箇条書きが必要な場合は「・」を使用してください"
    )

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation_history)

    user_content = (
        f"以下は社内資料の全文です。"
        f"これらの内容と会話の文脈を踏まえて、質問に詳しく回答してください。\n\n"
        f"【資料全文】\n{context_text}\n\n"
        f"【質問】\n{question}"
    )
    messages.append({"role": "user", "content": user_content})

    answer = await call_llm(messages)
    return answer, sorted(set(source_refs))


async def _process_rag_mode(
    db: Session,
    notebook_id: UUID,
    source_ids: Optional[List[str]],
    question: str,
    conversation_history: List[dict],
) -> tuple[str, List[str]]:
    """Process using RAG with vector similarity search."""
    from sqlalchemy import func, select, text

    from app.models.source_chunk import SourceChunk
    from app.services.rag_utils import format_embedding_for_pgvector

    # Get embedding for question
    embeddings = await embed_texts([question])
    if not embeddings or not embeddings[0]:
        return "埋め込み生成に失敗しました。", []

    query_embedding = embeddings[0]
    embedding_str = format_embedding_for_pgvector(query_embedding)

    # Build query for similar chunks
    k = 8
    similarity_threshold = 0.3

    if source_ids:
        uuid_source_ids = [UUID(sid) for sid in source_ids]
        chunks = db.execute(
            text(
                f"""
                SELECT sc.id, sc.source_id, sc.content, sc.page_number, s.title,
                       1 - (sc.embedding <-> '{embedding_str}'::vector) as similarity
                FROM source_chunks sc
                JOIN sources s ON sc.source_id = s.id
                WHERE sc.source_id = ANY(:source_ids)
                  AND s.notebook_id = :notebook_id
                ORDER BY sc.embedding <-> '{embedding_str}'::vector
                LIMIT :k
            """
            ),
            {"source_ids": uuid_source_ids, "notebook_id": notebook_id, "k": k},
        ).fetchall()
    else:
        chunks = db.execute(
            text(
                f"""
                SELECT sc.id, sc.source_id, sc.content, sc.page_number, s.title,
                       1 - (sc.embedding <-> '{embedding_str}'::vector) as similarity
                FROM source_chunks sc
                JOIN sources s ON sc.source_id = s.id
                WHERE s.notebook_id = :notebook_id
                ORDER BY sc.embedding <-> '{embedding_str}'::vector
                LIMIT :k
            """
            ),
            {"notebook_id": notebook_id, "k": k},
        ).fetchall()

    # Filter by similarity threshold
    relevant_chunks = [c for c in chunks if c.similarity >= similarity_threshold]

    if not relevant_chunks:
        return "関連する情報が見つかりませんでした。", []

    # Build context
    contexts = []
    source_refs = []

    for chunk in relevant_chunks:
        page_info = f"(p.{chunk.page_number})" if chunk.page_number else ""
        contexts.append(f"【{chunk.title}{page_info}】\n{chunk.content}")
        ref = f"{chunk.title}{page_info}"
        if ref not in source_refs:
            source_refs.append(ref)

    context_text = "\n\n---\n\n".join(contexts)

    system_prompt = (
        "あなたは社内資料の内容に基づいて回答するアシスタントです。\n"
        "以下のルールに従ってください：\n"
        "1. 提供された資料の内容を参考にして回答してください\n"
        "2. 資料にない情報については推測せず「分かりません」と答えてください\n"
        "3. 会話の文脈を考慮して、一貫性のある対話を心がけてください\n"
        "4. 回答はプレーンテキストで出力してください。マークダウン記法は使用しないでください\n"
        "5. 箇条書きが必要な場合は「・」を使用してください"
    )

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation_history)

    user_content = (
        f"以下は関連する資料からの抜粋です。\n\n"
        f"【関連資料】\n{context_text}\n\n"
        f"【質問】\n{question}"
    )
    messages.append({"role": "user", "content": user_content})

    answer = await call_llm(messages)
    return answer, source_refs


async def _process_free_mode(
    question: str,
    conversation_history: List[dict],
) -> str:
    """Process in free mode without RAG."""
    messages = [
        {
            "role": "system",
            "content": (
                "あなたは親切で知識豊富なアシスタントです。"
                "ユーザーの質問に対して、丁寧で分かりやすい回答を提供してください。"
                "会話の文脈を考慮して、一貫性のある対話を心がけてください。"
                "回答はプレーンテキストで出力してください。マークダウン記法は使用しないでください。"
                "箇条書きが必要な場合は「・」を使用してください。"
            ),
        },
    ]

    messages.extend(conversation_history)
    messages.append({"role": "user", "content": question})

    answer = await call_llm(messages)
    return answer


def start_chat_processing_background(
    message_id: UUID,
    db_url: str,
    notebook_id: UUID,
    session_id: Optional[UUID],
    question: str,
    source_ids: Optional[List[str]],
    use_rag: bool,
    use_formatted_text: bool,
):
    """
    Start chat processing in a background thread.

    Creates a new event loop for the background task to avoid
    issues with the main FastAPI event loop.
    """

    def run_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                process_chat_message_async(
                    message_id=message_id,
                    db_url=db_url,
                    notebook_id=notebook_id,
                    session_id=session_id,
                    question=question,
                    source_ids=source_ids,
                    use_rag=use_rag,
                    use_formatted_text=use_formatted_text,
                )
            )
        finally:
            loop.close()

    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()
    logger.info(f"Started background chat processing: {message_id}")
