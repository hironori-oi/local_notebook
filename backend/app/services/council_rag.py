"""
Council RAG (Retrieval-Augmented Generation) service.

This module handles:
- Vector similarity search for council agenda chunks
- Conversation history management within sessions
- LLM prompt construction with context from selected meetings/agendas
"""

import json
import logging
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import bindparam, func, select, text
from sqlalchemy.orm import Session
from sqlalchemy.types import String

from app.core.config import settings
from app.core.exceptions import BadRequestError, EmbeddingError, LLMConnectionError
from app.models.council_agenda_item import CouncilAgendaItem
from app.models.council_chat_session import CouncilChatSession
from app.models.council_meeting import CouncilMeeting
from app.models.council_message import CouncilMessage
from app.schemas.council_chat import CouncilChatRequest, CouncilChatResponse
from app.services.embedding import embed_texts
from app.services.llm_client import call_llm
from app.services.rag_utils import (
    format_embedding_for_pgvector,
    get_conversation_history_generic,
    update_session_timestamp,
)

logger = logging.getLogger(__name__)


def get_council_conversation_history(
    db: Session,
    session_id: UUID,
    max_messages: int = None,
    max_chars: int = None,
) -> List[Dict[str, str]]:
    """
    Retrieve conversation history from a council chat session.

    Args:
        db: Database session
        session_id: Council chat session ID
        max_messages: Maximum number of messages to include
        max_chars: Maximum total characters for history

    Returns:
        List of message dicts with 'role' and 'content' keys
    """
    return get_conversation_history_generic(
        db=db,
        session_id=session_id,
        message_model=CouncilMessage,
        max_messages=max_messages,
        max_chars=max_chars,
    )


async def council_rag_answer(
    db: Session,
    req: CouncilChatRequest,
    user_id: UUID,
    session_id: UUID,
) -> CouncilChatResponse:
    """
    Process a RAG query for council meetings with conversation history.

    Args:
        db: Database session
        req: Council chat request
        user_id: User ID
        session_id: Session ID for conversation history

    Returns:
        CouncilChatResponse with answer and sources

    Raises:
        BadRequestError: If meeting_ids don't belong to the council
        LLMConnectionError: If LLM service is unavailable
        EmbeddingError: If embedding service is unavailable
    """
    council_uuid = UUID(req.council_id)

    # Get conversation history
    conversation_history = get_council_conversation_history(db, session_id)
    logger.debug(f"Retrieved {len(conversation_history)} messages from session history")

    # Save user message
    user_message = CouncilMessage(
        session_id=session_id,
        role="user",
        content=req.question,
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    # Update session's updated_at timestamp
    update_session_timestamp(db, session_id, CouncilChatSession)

    # ==========================================================================
    # Free Input Mode (No RAG)
    # ==========================================================================
    if not req.use_rag:
        messages = [
            {
                "role": "system",
                "content": (
                    "あなたは審議会情報に詳しいアシスタントです。"
                    "ユーザーの質問に対して、丁寧で分かりやすい回答を提供してください。"
                    "会話の文脈を考慮して、一貫性のある対話を心がけてください。"
                    "回答はプレーンテキストで出力してください。マークダウン記法（#、*、**、-、```、>、|など）は使用しないでください。"
                    "箇条書きが必要な場合は「・」を使用してください。"
                ),
            },
        ]

        messages.extend(conversation_history)
        messages.append({"role": "user", "content": req.question})

        try:
            answer = await call_llm(messages)
        except Exception as e:
            logger.error(f"LLM call failed (free mode): {e}")
            raise LLMConnectionError(f"LLM service connection failed: {str(e)}")

        assistant_message = CouncilMessage(
            session_id=session_id,
            role="assistant",
            content=answer,
            source_refs=[],
        )
        db.add(assistant_message)
        db.commit()
        db.refresh(assistant_message)

        return CouncilChatResponse(
            answer=answer,
            sources=[],
            message_id=str(assistant_message.id),
            session_id=str(session_id),
        )

    # ==========================================================================
    # RAG Mode
    # ==========================================================================

    # 1. Get target meeting IDs with ownership validation
    if req.meeting_ids:
        meeting_ids = [UUID(mid) for mid in req.meeting_ids]

        # Validate all meeting_ids belong to the specified council
        valid_count = db.execute(
            select(func.count(CouncilMeeting.id)).where(
                CouncilMeeting.id.in_(meeting_ids),
                CouncilMeeting.council_id == council_uuid,
            )
        ).scalar()

        if valid_count != len(meeting_ids):
            logger.warning(
                f"User {user_id} attempted to access meetings not belonging to council {council_uuid}"
            )
            raise BadRequestError(
                "Some of the specified meeting IDs do not belong to this council"
            )
    else:
        # Use all meetings in the council
        rows = db.execute(
            select(CouncilMeeting.id).where(CouncilMeeting.council_id == council_uuid)
        )
        meeting_ids = [row[0] for row in rows]

    if not meeting_ids:
        answer = "This council has no meetings registered."
        assistant_message = CouncilMessage(
            session_id=session_id,
            role="assistant",
            content=answer,
            source_refs=[],
        )
        db.add(assistant_message)
        db.commit()
        db.refresh(assistant_message)
        return CouncilChatResponse(
            answer=answer,
            sources=[],
            message_id=str(assistant_message.id),
            session_id=str(session_id),
        )

    # 2. Generate question embedding
    try:
        [q_emb] = await embed_texts([req.question])
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise EmbeddingError(f"Embedding generation failed: {str(e)}")

    # 3. Similarity search in council_agenda_chunks (via agenda_items)
    k = 8
    q_emb_str = format_embedding_for_pgvector(q_emb)

    # Parse agenda_ids if provided
    agenda_ids = []
    if req.agenda_ids:
        agenda_ids = [UUID(aid) for aid in req.agenda_ids]

    # Build SQL dynamically based on whether agenda_ids filter is needed
    # This avoids the PostgreSQL type inference issue with empty arrays
    if agenda_ids:
        sql = text(
            """
            SELECT cac.id, cac.content, cac.chunk_type,
                   cai.agenda_number, cai.title as agenda_title, cai.id as agenda_id,
                   cm.meeting_number, cm.title as meeting_title, cm.id as meeting_id
            FROM council_agenda_chunks cac
            JOIN council_agenda_items cai ON cac.agenda_id = cai.id
            JOIN council_meetings cm ON cai.meeting_id = cm.id
            WHERE cai.meeting_id = ANY(:meeting_ids)
              AND cai.id = ANY(:agenda_ids)
            ORDER BY cac.embedding <-> CAST(:query_emb AS vector)
            LIMIT :limit
            """
        ).bindparams(bindparam("query_emb", type_=String))
        params = {
            "meeting_ids": meeting_ids,
            "agenda_ids": agenda_ids,
            "query_emb": q_emb_str,
            "limit": k,
        }
    else:
        sql = text(
            """
            SELECT cac.id, cac.content, cac.chunk_type,
                   cai.agenda_number, cai.title as agenda_title, cai.id as agenda_id,
                   cm.meeting_number, cm.title as meeting_title, cm.id as meeting_id
            FROM council_agenda_chunks cac
            JOIN council_agenda_items cai ON cac.agenda_id = cai.id
            JOIN council_meetings cm ON cai.meeting_id = cm.id
            WHERE cai.meeting_id = ANY(:meeting_ids)
            ORDER BY cac.embedding <-> CAST(:query_emb AS vector)
            LIMIT :limit
            """
        ).bindparams(bindparam("query_emb", type_=String))
        params = {
            "meeting_ids": meeting_ids,
            "query_emb": q_emb_str,
            "limit": k,
        }

    try:
        rows = db.execute(sql, params).fetchall()
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        raise BadRequestError(f"Similarity search failed: {str(e)}")

    contexts: List[str] = []
    source_refs: List[dict] = []

    for (
        _id,
        content,
        chunk_type,
        agenda_number,
        agenda_title,
        agenda_id,
        meeting_number,
        meeting_title,
        meeting_id,
    ) in rows:
        contexts.append(content)

        # Build source reference
        type_label = "Materials" if chunk_type == "materials" else "Minutes"
        ref_text = f"Meeting #{meeting_number}"
        if meeting_title:
            ref_text += f" {meeting_title}"
        ref_text += f" - Agenda #{agenda_number}"
        if agenda_title:
            ref_text += f" {agenda_title}"
        ref_text += f" ({type_label})"

        source_refs.append(
            {
                "meeting_id": str(meeting_id),
                "meeting_number": meeting_number,
                "agenda_id": str(agenda_id),
                "agenda_number": agenda_number,
                "agenda_title": agenda_title,
                "type": chunk_type,
                "excerpt": content[:100] + "..." if len(content) > 100 else content,
            }
        )

    # 4. Build LLM messages
    if not contexts:
        messages = [
            {
                "role": "system",
                "content": (
                    "審議会資料・議事録に基づいて回答するアシスタントです。"
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
            raise LLMConnectionError(f"LLM service connection failed: {str(e)}")

        assistant_message = CouncilMessage(
            session_id=session_id,
            role="assistant",
            content=answer,
            source_refs=[],
        )
        db.add(assistant_message)
        db.commit()
        db.refresh(assistant_message)
        return CouncilChatResponse(
            answer=answer,
            sources=[],
            message_id=str(assistant_message.id),
            session_id=str(session_id),
        )

    # Build context text
    context_text = "\n\n---\n\n".join(contexts)

    # Build system prompt
    system_prompt = (
        "あなたは審議会の資料・議事録の内容に基づいて回答するアシスタントです。\n"
        "以下のルールに従ってください：\n"
        "1. 提供された資料・議事録の内容に基づいて回答してください\n"
        "2. 資料にない情報については推測せず「分かりません」と答えてください\n"
        "3. 会話の文脈を考慮して、一貫性のある対話を心がけてください\n"
        "4. 発言者の主張や立場を正確に伝えてください\n"
        "5. 数値やデータは正確に引用してください\n"
        "6. 回答はプレーンテキストで出力してください。マークダウン記法（#、*、**、-、```、>、|など）は使用しないでください\n"
        "7. 箇条書きが必要な場合は「・」を使用してください"
    )

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation_history)

    user_content = (
        f"以下は審議会の資料・議事録から抽出した関連部分です。"
        f"これらの内容と会話の文脈を踏まえて、質問に回答してください。\n\n"
        f"【資料・議事録抜粋】\n{context_text}\n\n"
        f"【質問】\n{req.question}"
    )
    messages.append({"role": "user", "content": user_content})

    try:
        answer = await call_llm(messages)
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        raise LLMConnectionError(f"LLM service connection failed: {str(e)}")

    # Deduplicate source refs
    unique_refs = []
    seen = set()
    for ref in source_refs:
        key = (ref["agenda_id"], ref["type"])
        if key not in seen:
            seen.add(key)
            unique_refs.append(ref)

    # Save assistant message
    assistant_message = CouncilMessage(
        session_id=session_id,
        role="assistant",
        content=answer,
        source_refs=unique_refs,
    )
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)

    return CouncilChatResponse(
        answer=answer,
        sources=unique_refs,
        message_id=str(assistant_message.id),
        session_id=str(session_id),
    )
