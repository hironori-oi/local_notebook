"""
RAG (Retrieval-Augmented Generation) service with session-based conversation history.

This module handles:
- Vector similarity search for relevant document chunks
- Conversation history management within sessions
- LLM prompt construction with context
"""
import logging
from typing import List, Optional, Dict
from uuid import UUID
import json

from sqlalchemy.orm import Session
from sqlalchemy import select, text, func, bindparam
from sqlalchemy.types import String

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.embedding import embed_texts
from app.services.llm_client import call_llm
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
    if max_messages is None:
        max_messages = settings.MAX_CHAT_HISTORY_MESSAGES
    if max_chars is None:
        max_chars = settings.MAX_CHAT_HISTORY_CHARS

    # Get messages ordered by creation time (oldest first)
    messages = db.query(Message).filter(
        Message.session_id == session_id
    ).order_by(
        Message.created_at.asc()
    ).all()

    if not messages:
        return []

    # Convert to LLM format and apply limits
    history = []
    total_chars = 0

    # Process from newest to oldest to prioritize recent messages
    for msg in reversed(messages):
        msg_content = msg.content
        msg_chars = len(msg_content)

        # Check if adding this message would exceed limits
        if len(history) >= max_messages:
            break
        if total_chars + msg_chars > max_chars:
            # Try to include a truncated version
            remaining_chars = max_chars - total_chars
            if remaining_chars > 100:  # Only include if we can show meaningful content
                msg_content = msg_content[:remaining_chars] + "..."
                history.insert(0, {"role": msg.role, "content": msg_content})
            break

        history.insert(0, {"role": msg.role, "content": msg_content})
        total_chars += msg_chars

    return history


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
        db.query(ChatSession).filter(
            ChatSession.id == session_id
        ).update({"updated_at": func.now()})
        db.commit()

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
    # Convert embedding list to pgvector string format '[1.0, 2.0, ...]'
    q_emb_str = "[" + ",".join(str(x) for x in q_emb) + "]"

    # Use CAST syntax to avoid SQLAlchemy misinterpreting ::vector
    sql = text(
        """
        SELECT sc.id, sc.content, sc.page_number, s.title
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

    for _id, content, page_number, title in rows:
        contexts.append(content)
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
        "4. 前の会話で言及した内容を踏まえて回答してください"
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
