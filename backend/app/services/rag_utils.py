"""
Common RAG (Retrieval-Augmented Generation) utilities.

This module provides shared functionality for RAG services:
- Conversation history retrieval
- LLM message building
- Context text construction
"""
import logging
from typing import List, Dict, Optional, Any, TypeVar
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.config import settings

logger = logging.getLogger(__name__)

# Type variable for message models
MessageModel = TypeVar("MessageModel")
SessionModel = TypeVar("SessionModel")


def get_conversation_history_generic(
    db: Session,
    session_id: UUID,
    message_model: Any,
    session_id_field: str = "session_id",
    created_at_field: str = "created_at",
    max_messages: Optional[int] = None,
    max_chars: Optional[int] = None,
) -> List[Dict[str, str]]:
    """
    Generic conversation history retrieval.

    Args:
        db: Database session
        session_id: Chat session ID
        message_model: SQLAlchemy model class for messages
        session_id_field: Name of the session ID field in the model
        created_at_field: Name of the created_at field in the model
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
    session_filter = getattr(message_model, session_id_field)
    created_at = getattr(message_model, created_at_field)

    messages = db.query(message_model).filter(
        session_filter == session_id
    ).order_by(
        created_at.asc()
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

        if len(history) >= max_messages:
            break
        if total_chars + msg_chars > max_chars:
            remaining_chars = max_chars - total_chars
            if remaining_chars > 100:
                msg_content = msg_content[:remaining_chars] + "..."
                history.insert(0, {"role": msg.role, "content": msg_content})
            break

        history.insert(0, {"role": msg.role, "content": msg_content})
        total_chars += msg_chars

    return history


def update_session_timestamp(
    db: Session,
    session_id: UUID,
    session_model: Any,
) -> None:
    """
    Update a chat session's updated_at timestamp.

    Args:
        db: Database session
        session_id: Session ID to update
        session_model: SQLAlchemy model class for sessions
    """
    db.query(session_model).filter(
        session_model.id == session_id
    ).update({"updated_at": func.now()})
    db.commit()


def build_context_text(
    contexts: List[str],
    separator: str = "\n\n---\n\n",
    max_chars: Optional[int] = None,
    truncation_message: str = "\n\n[...テキストが長いため一部省略...]",
) -> str:
    """
    Build context text from a list of context strings.

    Args:
        contexts: List of context strings
        separator: Separator between contexts
        max_chars: Maximum characters (truncate if exceeded)
        truncation_message: Message to append when truncated

    Returns:
        Combined context text
    """
    context_text = separator.join(contexts)

    if max_chars and len(context_text) > max_chars:
        context_text = context_text[:max_chars] + truncation_message

    return context_text


def build_rag_system_prompt(
    domain: str = "社内資料",
    additional_rules: Optional[List[str]] = None,
) -> str:
    """
    Build a standard RAG system prompt.

    Args:
        domain: The domain of documents (e.g., "社内資料", "審議会資料")
        additional_rules: Additional rules to include

    Returns:
        System prompt string
    """
    base_rules = [
        f"提供された{domain}の内容に基づいて回答してください",
        "資料にない情報については推測せず「分かりません」と答えてください",
        "会話の文脈を考慮して、一貫性のある対話を心がけてください",
        "回答はプレーンテキストで出力してください。マークダウン記法（#、*、**、-、```、>、|など）は使用しないでください",
        "箇条書きが必要な場合は「・」を使用してください",
    ]

    if additional_rules:
        base_rules.extend(additional_rules)

    rules_text = "\n".join(f"{i+1}. {rule}" for i, rule in enumerate(base_rules))

    return (
        f"あなたは{domain}の内容に基づいて回答するアシスタントです。\n"
        f"以下のルールに従ってください：\n{rules_text}"
    )


def build_free_mode_system_prompt(domain: str = "知識豊富な") -> str:
    """
    Build a system prompt for free input mode (no RAG).

    Args:
        domain: Description of the assistant's domain

    Returns:
        System prompt string
    """
    return (
        f"あなたは親切で{domain}アシスタントです。"
        "ユーザーの質問に対して、丁寧で分かりやすい回答を提供してください。"
        "会話の文脈を考慮して、一貫性のある対話を心がけてください。"
        "回答はプレーンテキストで出力してください。マークダウン記法（#、*、**、-、```、>、|など）は使用しないでください。"
        "箇条書きが必要な場合は「・」を使用してください。"
    )


def build_llm_messages(
    system_prompt: str,
    conversation_history: List[Dict[str, str]],
    user_content: str,
) -> List[Dict[str, str]]:
    """
    Build LLM messages list.

    Args:
        system_prompt: System prompt content
        conversation_history: Previous conversation messages
        user_content: Current user message content

    Returns:
        List of message dicts for LLM
    """
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_content})
    return messages


def format_embedding_for_pgvector(embedding: List[float]) -> str:
    """
    Format an embedding vector for PostgreSQL pgvector.

    Args:
        embedding: List of float values

    Returns:
        String in pgvector format '[1.0, 2.0, ...]'
    """
    return "[" + ",".join(str(x) for x in embedding) + "]"
