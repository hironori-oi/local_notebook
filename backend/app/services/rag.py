"""
RAG (Retrieval-Augmented Generation) service with session-based conversation history.

This module handles:
- Vector similarity search for relevant document chunks
- Conversation history management within sessions
- LLM prompt construction with context
- Streaming responses for improved UX
"""
import logging
from typing import List, Optional, Dict, AsyncGenerator
from uuid import UUID
import json

from sqlalchemy.orm import Session
from sqlalchemy import select, text, func, bindparam
from sqlalchemy.types import String

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.embedding import embed_texts
from app.services.llm_client import call_llm, get_llm_client
from app.services.rag_utils import (
    get_conversation_history_generic,
    update_session_timestamp,
    build_context_text,
    build_llm_messages,
    format_embedding_for_pgvector,
)
from app.models.source import Source
from app.models.message import Message
from app.models.chat_session import ChatSession
from app.core.config import settings
from app.core.exceptions import BadRequestError, LLMConnectionError, EmbeddingError

logger = logging.getLogger(__name__)


def get_conversation_history(
    db: Session,
    session_id: UUID,
    max_messages: int = None,
    max_chars: int = None,
) -> List[Dict[str, str]]:
    """
    Retrieve conversation history from a session for LLM context.

    Args:
        db: Database session
        session_id: Chat session ID
        max_messages: Maximum number of messages to include
        max_chars: Maximum total characters for history

    Returns:
        List of message dicts with 'role' and 'content' keys
    """
    return get_conversation_history_generic(
        db=db,
        session_id=session_id,
        message_model=Message,
        max_messages=max_messages,
        max_chars=max_chars,
    )


async def rag_answer(
    db: Session,
    req: ChatRequest,
    user_id: Optional[UUID] = None,
    session_id: Optional[UUID] = None,
) -> ChatResponse:
    """
    Process a RAG query with conversation history and save messages to the database.

    Args:
        db: Database session
        req: Chat request containing notebook_id, source_ids, question, and use_rag
        user_id: Optional user ID for message attribution
        session_id: Optional session ID for conversation history

    Returns:
        ChatResponse with answer, sources, and message_id

    Raises:
        BadRequestError: If source_ids don't belong to the notebook
        LLMConnectionError: If LLM service is unavailable
        EmbeddingError: If embedding service is unavailable
    """
    notebook_uuid = UUID(req.notebook_id)

    # Get conversation history if session exists
    conversation_history = []
    if session_id:
        conversation_history = get_conversation_history(db, session_id)
        logger.debug(f"Retrieved {len(conversation_history)} messages from session history")

    # Save user message
    user_message = Message(
        notebook_id=notebook_uuid,
        session_id=session_id,
        user_id=user_id,
        role="user",
        content=req.question,
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    # Update session's updated_at timestamp
    if session_id:
        update_session_timestamp(db, session_id, ChatSession)

    # ==========================================================================
    # Formatted Text Mode (Full Document Context)
    # ==========================================================================
    if req.use_formatted_text:
        notebook_uuid = UUID(req.notebook_id)

        # Get target source IDs with ownership validation
        if req.source_ids:
            source_ids = [UUID(sid) for sid in req.source_ids]

            # SECURITY: Validate all source_ids belong to the specified notebook
            valid_count = db.execute(
                select(func.count(Source.id)).where(
                    Source.id.in_(source_ids),
                    Source.notebook_id == notebook_uuid
                )
            ).scalar()

            if valid_count != len(source_ids):
                logger.warning(
                    f"User {user_id} attempted to access sources not belonging to notebook {notebook_uuid}"
                )
                raise BadRequestError(
                    "指定されたソースIDの一部がこのノートブックに存在しません"
                )
        else:
            rows = db.execute(
                select(Source.id).where(Source.notebook_id == notebook_uuid)
            )
            source_ids = [row[0] for row in rows]

        if not source_ids:
            answer = "このNotebookにはソースが登録されていません。"
            assistant_message = Message(
                notebook_id=notebook_uuid,
                session_id=session_id,
                user_id=None,
                role="assistant",
                content=answer,
                source_refs=json.dumps([]),
            )
            db.add(assistant_message)
            db.commit()
            db.refresh(assistant_message)
            return ChatResponse(
                answer=answer,
                sources=[],
                message_id=str(assistant_message.id),
            )

        # Get formatted_text from sources
        sources = db.query(Source).filter(
            Source.id.in_(source_ids)
        ).all()

        contexts: List[str] = []
        source_refs: List[str] = []

        for source in sources:
            # Use formatted_text if available, otherwise fall back to full_text
            text_content = source.formatted_text or source.full_text
            if text_content:
                contexts.append(f"【{source.title}】\n{text_content}")
                source_refs.append(source.title)

        if not contexts:
            answer = "選択されたソースにはテキストデータがありません。処理が完了するまでお待ちください。"
            assistant_message = Message(
                notebook_id=notebook_uuid,
                session_id=session_id,
                user_id=None,
                role="assistant",
                content=answer,
                source_refs=json.dumps([]),
            )
            db.add(assistant_message)
            db.commit()
            db.refresh(assistant_message)
            return ChatResponse(
                answer=answer,
                sources=[],
                message_id=str(assistant_message.id),
            )

        # Build context text from formatted texts
        context_text = "\n\n---\n\n".join(contexts)

        # Truncate if too long (to avoid context window limits)
        max_context_chars = 30000  # Adjust based on model's context window
        if len(context_text) > max_context_chars:
            context_text = context_text[:max_context_chars] + "\n\n[...テキストが長いため一部省略...]"

        # Build system prompt for formatted text mode
        system_prompt = (
            "あなたは社内資料の内容に基づいて回答するアシスタントです。\n"
            "以下のルールに従ってください：\n"
            "1. 提供された資料の全文を参照して、詳細かつ正確に回答してください\n"
            "2. 資料にない情報については推測せず「分かりません」と答えてください\n"
            "3. 会話の文脈を考慮して、一貫性のある対話を心がけてください\n"
            "4. 資料の内容を引用・要約する際は、元の情報を正確に伝えてください\n"
            "5. 回答はプレーンテキストで出力してください。マークダウン記法（#、*、**、-、```、>、|など）は使用しないでください\n"
            "6. 箇条書きが必要な場合は「・」を使用してください"
        )

        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history
        messages.extend(conversation_history)

        # Add current question with context
        user_content = (
            f"以下は社内資料の全文です。"
            f"これらの内容と会話の文脈を踏まえて、質問に詳しく回答してください。\n\n"
            f"【資料全文】\n{context_text}\n\n"
            f"【質問】\n{req.question}"
        )
        messages.append({"role": "user", "content": user_content})

        try:
            answer = await call_llm(messages)
        except Exception as e:
            logger.error(f"LLM call failed (formatted text mode): {e}")
            raise LLMConnectionError(f"LLMサービスへの接続に失敗しました: {str(e)}")

        unique_refs = sorted(set(source_refs))

        # Save assistant message
        assistant_message = Message(
            notebook_id=notebook_uuid,
            session_id=session_id,
            user_id=None,
            role="assistant",
            content=answer,
            source_refs=json.dumps(unique_refs),
        )
        db.add(assistant_message)
        db.commit()
        db.refresh(assistant_message)

        return ChatResponse(
            answer=answer,
            sources=unique_refs,
            message_id=str(assistant_message.id),
        )

    # ==========================================================================
    # Free Input Mode (No RAG)
    # ==========================================================================
    if not req.use_rag:
        messages = [
            {
                "role": "system",
                "content": (
                    "あなたは親切で知識豊富なアシスタントです。"
                    "ユーザーの質問に対して、丁寧で分かりやすい回答を提供してください。"
                    "会話の文脈を考慮して、一貫性のある対話を心がけてください。"
                    "回答はプレーンテキストで出力してください。マークダウン記法（#、*、**、-、```、>、|など）は使用しないでください。"
                    "箇条書きが必要な場合は「・」を使用してください。"
                ),
            },
        ]

        # Add conversation history
        messages.extend(conversation_history)

        # Add current question
        messages.append({"role": "user", "content": req.question})

        try:
            answer = await call_llm(messages)
        except Exception as e:
            logger.error(f"LLM call failed (free mode): {e}")
            raise LLMConnectionError(f"LLMサービスへの接続に失敗しました: {str(e)}")

        assistant_message = Message(
            notebook_id=notebook_uuid,
            session_id=session_id,
            user_id=None,
            role="assistant",
            content=answer,
            source_refs=json.dumps([]),
        )
        db.add(assistant_message)
        db.commit()
        db.refresh(assistant_message)

        return ChatResponse(
            answer=answer,
            sources=[],
            message_id=str(assistant_message.id),
        )

    # ==========================================================================
    # RAG Mode
    # ==========================================================================

    # 1. Get target source IDs with ownership validation
    if req.source_ids:
        source_ids = [UUID(sid) for sid in req.source_ids]

        # SECURITY: Validate all source_ids belong to the specified notebook
        valid_count = db.execute(
            select(func.count(Source.id)).where(
                Source.id.in_(source_ids),
                Source.notebook_id == notebook_uuid
            )
        ).scalar()

        if valid_count != len(source_ids):
            logger.warning(
                f"User {user_id} attempted to access sources not belonging to notebook {notebook_uuid}"
            )
            raise BadRequestError(
                "指定されたソースIDの一部がこのノートブックに存在しません"
            )
    else:
        rows = db.execute(
            select(Source.id).where(Source.notebook_id == notebook_uuid)
        )
        source_ids = [row[0] for row in rows]

    if not source_ids:
        answer = "このNotebookにはソースが登録されていません。"
        assistant_message = Message(
            notebook_id=notebook_uuid,
            session_id=session_id,
            user_id=None,
            role="assistant",
            content=answer,
            source_refs=json.dumps([]),
        )
        db.add(assistant_message)
        db.commit()
        db.refresh(assistant_message)
        return ChatResponse(
            answer=answer,
            sources=[],
            message_id=str(assistant_message.id),
        )

    # 2. Generate question embedding with error handling
    try:
        [q_emb] = await embed_texts([req.question])
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise EmbeddingError(f"埋め込み生成に失敗しました: {str(e)}")

    # 3. Similarity search with error handling
    k = 8
    similarity_threshold = 0.3  # Minimum similarity score to include in results
    # Convert embedding list to pgvector string format '[1.0, 2.0, ...]'
    q_emb_str = "[" + ",".join(str(x) for x in q_emb) + "]"

    # Use CAST syntax to avoid SQLAlchemy misinterpreting ::vector
    # Include similarity score (1 - distance) for context quality filtering
    sql = text(
        """
        SELECT sc.id, sc.content, sc.page_number, s.title,
               1 - (sc.embedding <-> CAST(:query_emb AS vector)) AS similarity
        FROM source_chunks sc
        JOIN sources s ON sc.source_id = s.id
        WHERE sc.source_id = ANY(:source_ids)
        ORDER BY sc.embedding <-> CAST(:query_emb AS vector)
        LIMIT :limit
        """
    ).bindparams(bindparam("query_emb", type_=String))

    try:
        rows = db.execute(
            sql,
            {
                "source_ids": source_ids,
                "query_emb": q_emb_str,
                "limit": k,
            },
        ).fetchall()
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        raise BadRequestError(f"類似検索に失敗しました: {str(e)}")

    contexts: List[str] = []
    source_refs: List[str] = []

    for _id, content, page_number, title, similarity in rows:
        # Filter out low-similarity results for better answer quality
        if similarity < similarity_threshold:
            logger.debug(f"Skipping chunk from {title} with low similarity: {similarity:.2%}")
            continue

        # Build context with source attribution and relevance indicator
        page_info = f"p.{page_number}" if page_number else "全体"
        context_header = f"【{title} ({page_info}, 関連度: {similarity:.0%})】"
        contexts.append(f"{context_header}\n{content}")

        ref = f"{title}"
        if page_number:
            ref += f"(p.{page_number})"
        source_refs.append(ref)

    # 4. Build LLM messages with history and context
    if not contexts:
        # No relevant documents found
        messages = [
            {
                "role": "system",
                "content": (
                    "社内資料に基づいて回答するアシスタントです。"
                    "資料が見つからない場合は分からないと答えてください。"
                    "会話の文脈を考慮して対話してください。"
                    "回答はプレーンテキストで出力してください。マークダウン記法は使用しないでください。"
                ),
            },
        ]
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": req.question})

        try:
            answer = await call_llm(messages)
        except Exception as e:
            logger.error(f"LLM call failed (no context): {e}")
            raise LLMConnectionError(f"LLMサービスへの接続に失敗しました: {str(e)}")

        assistant_message = Message(
            notebook_id=notebook_uuid,
            session_id=session_id,
            user_id=None,
            role="assistant",
            content=answer,
            source_refs=json.dumps([]),
        )
        db.add(assistant_message)
        db.commit()
        db.refresh(assistant_message)
        return ChatResponse(
            answer=answer,
            sources=[],
            message_id=str(assistant_message.id),
        )

    # Build context text from retrieved chunks
    context_text = "\n\n---\n\n".join(contexts)

    # Build system prompt
    system_prompt = (
        "あなたは社内資料の内容に基づいて回答するアシスタントです。\n"
        "以下のルールに従ってください：\n"
        "1. 提供された資料の内容に基づいて回答してください\n"
        "2. 資料にない情報については推測せず「分かりません」と答えてください\n"
        "3. 会話の文脈を考慮して、一貫性のある対話を心がけてください\n"
        "4. 前の会話で言及した内容を踏まえて回答してください\n"
        "5. 回答はプレーンテキストで出力してください。マークダウン記法（#、*、**、-、```、>、|など）は使用しないでください\n"
        "6. 箇条書きが必要な場合は「・」を使用してください"
    )

    messages = [{"role": "system", "content": system_prompt}]

    # Add conversation history
    messages.extend(conversation_history)

    # Add current question with context
    user_content = (
        f"以下は社内資料から抽出した関連部分です。"
        f"これらの内容と会話の文脈を踏まえて、質問に回答してください。\n\n"
        f"【資料抜粋】\n{context_text}\n\n"
        f"【質問】\n{req.question}"
    )
    messages.append({"role": "user", "content": user_content})

    try:
        answer = await call_llm(messages)
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        raise LLMConnectionError(f"LLMサービスへの接続に失敗しました: {str(e)}")

    unique_refs = sorted(set(source_refs))

    # Save assistant message
    assistant_message = Message(
        notebook_id=notebook_uuid,
        session_id=session_id,
        user_id=None,
        role="assistant",
        content=answer,
        source_refs=json.dumps(unique_refs),
    )
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)

    return ChatResponse(
        answer=answer,
        sources=unique_refs,
        message_id=str(assistant_message.id),
    )


async def rag_answer_stream(
    db: Session,
    req: ChatRequest,
    user_id: Optional[UUID] = None,
    session_id: Optional[UUID] = None,
) -> AsyncGenerator[str, None]:
    """
    Process a RAG query with streaming response.

    Yields SSE-formatted chunks as the LLM generates them.
    Message is saved to database after streaming completes.

    Args:
        db: Database session
        req: Chat request containing notebook_id, source_ids, question, and use_rag
        user_id: Optional user ID for message attribution
        session_id: Optional session ID for conversation history

    Yields:
        SSE-formatted strings: "data: <content>\\n\\n" for content,
        "data: [DONE]\\n\\n" for completion

    Raises:
        BadRequestError: If source_ids don't belong to the notebook
        LLMConnectionError: If LLM service is unavailable
        EmbeddingError: If embedding service is unavailable
    """
    notebook_uuid = UUID(req.notebook_id)

    # Get conversation history if session exists
    conversation_history = []
    if session_id:
        conversation_history = get_conversation_history(db, session_id)

    # Save user message
    user_message = Message(
        notebook_id=notebook_uuid,
        session_id=session_id,
        user_id=user_id,
        role="user",
        content=req.question,
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    # Update session's updated_at timestamp
    if session_id:
        update_session_timestamp(db, session_id, ChatSession)

    # Get sources and build context (similar to rag_answer)
    if req.source_ids:
        source_ids = [UUID(sid) for sid in req.source_ids]
        valid_count = db.execute(
            select(func.count(Source.id)).where(
                Source.id.in_(source_ids),
                Source.notebook_id == notebook_uuid
            )
        ).scalar()

        if valid_count != len(source_ids):
            raise BadRequestError("指定されたソースIDの一部がこのノートブックに存在しません")
    else:
        rows = db.execute(
            select(Source.id).where(Source.notebook_id == notebook_uuid)
        )
        source_ids = [row[0] for row in rows]

    if not source_ids:
        yield "data: このNotebookにはソースが登録されていません。\n\n"
        yield "data: [DONE]\n\n"
        return

    # Generate question embedding
    try:
        [q_emb] = await embed_texts([req.question])
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise EmbeddingError(f"埋め込み生成に失敗しました: {str(e)}")

    # Similarity search
    k = 8
    similarity_threshold = 0.3
    q_emb_str = "[" + ",".join(str(x) for x in q_emb) + "]"

    sql = text(
        """
        SELECT sc.id, sc.content, sc.page_number, s.title,
               1 - (sc.embedding <-> CAST(:query_emb AS vector)) AS similarity
        FROM source_chunks sc
        JOIN sources s ON sc.source_id = s.id
        WHERE sc.source_id = ANY(:source_ids)
        ORDER BY sc.embedding <-> CAST(:query_emb AS vector)
        LIMIT :limit
        """
    ).bindparams(bindparam("query_emb", type_=String))

    rows = db.execute(
        sql,
        {"source_ids": source_ids, "query_emb": q_emb_str, "limit": k},
    ).fetchall()

    contexts: List[str] = []
    source_refs: List[str] = []

    for _id, content, page_number, title, similarity in rows:
        if similarity < similarity_threshold:
            continue
        page_info = f"p.{page_number}" if page_number else "全体"
        context_header = f"【{title} ({page_info}, 関連度: {similarity:.0%})】"
        contexts.append(f"{context_header}\n{content}")
        ref = f"{title}"
        if page_number:
            ref += f"(p.{page_number})"
        source_refs.append(ref)

    # Build LLM messages
    system_prompt = (
        "あなたは社内資料の内容に基づいて回答するアシスタントです。\n"
        "以下のルールに従ってください：\n"
        "1. 提供された資料の内容に基づいて回答してください\n"
        "2. 資料にない情報については推測せず「分かりません」と答えてください\n"
        "3. 会話の文脈を考慮して、一貫性のある対話を心がけてください\n"
        "4. 回答はプレーンテキストで出力してください。マークダウン記法は使用しないでください\n"
        "5. 箇条書きが必要な場合は「・」を使用してください"
    )

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation_history)

    if contexts:
        context_text = "\n\n---\n\n".join(contexts)
        user_content = (
            f"以下は社内資料から抽出した関連部分です。"
            f"これらの内容と会話の文脈を踏まえて、質問に回答してください。\n\n"
            f"【資料抜粋】\n{context_text}\n\n"
            f"【質問】\n{req.question}"
        )
    else:
        user_content = req.question

    messages.append({"role": "user", "content": user_content})

    # Stream LLM response
    full_response = ""
    llm_client = get_llm_client()

    try:
        async for chunk in llm_client.chat_stream(messages):
            full_response += chunk
            # Escape newlines for SSE format
            escaped_chunk = chunk.replace("\n", "\\n")
            yield f"data: {escaped_chunk}\n\n"
    except Exception as e:
        logger.error(f"LLM streaming failed: {e}")
        yield f"data: [ERROR] {str(e)}\n\n"
        return

    # Send completion signal with sources
    unique_refs = sorted(set(source_refs))
    yield f"data: [SOURCES]{json.dumps(unique_refs)}\n\n"
    yield "data: [DONE]\n\n"

    # Save assistant message to database
    assistant_message = Message(
        notebook_id=notebook_uuid,
        session_id=session_id,
        user_id=None,
        role="assistant",
        content=full_response,
        source_refs=json.dumps(unique_refs),
    )
    db.add(assistant_message)
    db.commit()
