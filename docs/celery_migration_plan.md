# Celery 非同期タスク移行計画

## 概要

FastAPI BackgroundTasks をすべて Celery + Redis に移行し、タスクの永続化・リカバリー・スケーラビリティを実現する。

---

## 現状分析

### 移行対象タスク一覧

| # | タスク | ファイル | 現在の実装 | 処理時間 | 優先度 |
|---|--------|----------|-----------|---------|--------|
| 1 | ~~YouTube文字起こし~~ | youtube_transcriber.py | **Celery移行済** | 長 (30-60分) | - |
| 2 | ソースコンテンツ処理 | content_processor.py | BackgroundTask | 中 (1-5分) | 高 |
| 3 | 議事録処理 | content_processor.py | BackgroundTask | 中 (1-3分) | 高 |
| 4 | 議会アジェンダ処理 | council_content_processor.py | BackgroundTask | 中 (1-5分) | 中 |
| 5 | 議会アジェンダ資料処理 | council_content_processor.py | BackgroundTask | 中 (1-3分) | 中 |
| 6 | 議会アジェンダ議事録処理 | council_content_processor.py | BackgroundTask | 中 (1-3分) | 中 |
| 7 | 議会サマリー再生成 | council_content_processor.py | BackgroundTask | 短 (30秒-1分) | 低 |
| 8 | 文書チェック | document_checker.py | BackgroundTask | 中 (1-3分) | 高 |
| 9 | スライド生成 | slide_generator.py | BackgroundTask | 中 (2-5分) | 高 |
| 10 | チャット処理 | chat_processor.py | Thread | 短 (10-60秒) | 最高 |

### タスク分類

```
┌─────────────────────────────────────────────────────────────┐
│                    タスク処理時間分類                         │
├─────────────────────────────────────────────────────────────┤
│ 長時間 (>10分)  │ transcription                             │
│ 中時間 (1-10分) │ source, minute, agenda, document, slide  │
│ 短時間 (<1分)   │ chat, summary_regenerate                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 2: コンテンツ処理タスク移行

### 2.1 新規ファイル構成

```
backend/app/celery_app/tasks/
├── __init__.py           # UPDATE
├── base.py               # UPDATE: リカバリー関数追加
├── transcription.py      # 既存
├── content.py            # NEW: ソース・議事録処理
├── council.py            # NEW: 議会関連処理
├── document.py           # NEW: 文書チェック
├── slide.py              # NEW: スライド生成
└── chat.py               # NEW: チャット処理
```

### 2.2 キュー設計

```python
# backend/app/celery_app/config.py

# タスクルーティング
task_routes = {
    # 長時間タスク (専用ワーカー推奨)
    "app.celery_app.tasks.transcription.*": {"queue": "transcription"},

    # コンテンツ処理 (Embedding + LLM)
    "app.celery_app.tasks.content.*": {"queue": "content"},
    "app.celery_app.tasks.council.*": {"queue": "content"},

    # LLM集中タスク
    "app.celery_app.tasks.document.*": {"queue": "llm"},
    "app.celery_app.tasks.slide.*": {"queue": "llm"},

    # 低レイテンシー必須 (チャット)
    "app.celery_app.tasks.chat.*": {"queue": "chat"},
}

# キュー別設定
QUEUE_CONFIGS = {
    "transcription": {
        "time_limit": 3600,      # 1時間
        "soft_time_limit": 3300,
        "max_retries": 2,
    },
    "content": {
        "time_limit": 600,       # 10分
        "soft_time_limit": 540,
        "max_retries": 3,
    },
    "llm": {
        "time_limit": 600,       # 10分
        "soft_time_limit": 540,
        "max_retries": 3,
    },
    "chat": {
        "time_limit": 120,       # 2分
        "soft_time_limit": 100,
        "max_retries": 1,        # チャットはリトライ少なめ
    },
}
```

### 2.3 タスク実装パターン

#### content.py - ソース・議事録処理

```python
"""Celery tasks for content processing (sources, minutes)."""

import logging
import asyncio
from uuid import UUID
from celery import shared_task
from app.celery_app.tasks.base import DatabaseTask
from app.celery_app.config import RETRY_CONFIG, RETRYABLE_EXCEPTIONS

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    base=DatabaseTask,
    name="app.celery_app.tasks.content.process_source",
    queue="content",
    autoretry_for=RETRYABLE_EXCEPTIONS,
    max_retries=3,
    retry_backoff=True,
)
def process_source_task(self, source_id: str, raw_text: str):
    """
    Process source content: chunking, embedding, formatting, summary.

    Args:
        source_id: Source UUID string
        raw_text: Raw text extracted from document
    """
    from app.models.source import Source
    from app.services.content_processor import process_source_content

    logger.info(f"Processing source content: {source_id}")
    db = self.db

    try:
        source = db.query(Source).filter(Source.id == UUID(source_id)).first()
        if not source:
            logger.error(f"Source not found: {source_id}")
            return {"status": "error", "message": "Source not found"}

        # Run async processing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(process_source_content(db, UUID(source_id), raw_text))
        finally:
            loop.close()

        logger.info(f"Source content processed: {source_id}")
        return {"status": "completed", "source_id": source_id}

    except RETRYABLE_EXCEPTIONS as e:
        logger.warning(f"Retryable error for source {source_id}: {e}")
        raise
    except Exception as e:
        logger.error(f"Source processing failed: {e}", exc_info=True)
        _mark_source_failed(db, source_id, str(e))
        return {"status": "failed", "message": str(e)}


@shared_task(
    bind=True,
    base=DatabaseTask,
    name="app.celery_app.tasks.content.process_minute",
    queue="content",
    autoretry_for=RETRYABLE_EXCEPTIONS,
    max_retries=3,
    retry_backoff=True,
)
def process_minute_task(self, minute_id: str):
    """
    Process minute content: formatting, summary generation.

    Args:
        minute_id: Minute UUID string
    """
    from app.models.minute import Minute
    from app.services.content_processor import process_minute_content

    logger.info(f"Processing minute content: {minute_id}")
    db = self.db

    try:
        minute = db.query(Minute).filter(Minute.id == UUID(minute_id)).first()
        if not minute:
            logger.error(f"Minute not found: {minute_id}")
            return {"status": "error", "message": "Minute not found"}

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(process_minute_content(db, UUID(minute_id)))
        finally:
            loop.close()

        logger.info(f"Minute content processed: {minute_id}")
        return {"status": "completed", "minute_id": minute_id}

    except RETRYABLE_EXCEPTIONS as e:
        logger.warning(f"Retryable error for minute {minute_id}: {e}")
        raise
    except Exception as e:
        logger.error(f"Minute processing failed: {e}", exc_info=True)
        _mark_minute_failed(db, minute_id, str(e))
        return {"status": "failed", "message": str(e)}


# Helper functions
def _mark_source_failed(db, source_id: str, error: str):
    from app.models.source import Source
    try:
        source = db.query(Source).filter(Source.id == UUID(source_id)).first()
        if source:
            source.processing_status = "failed"
            source.processing_error = error
            db.commit()
    except Exception as e:
        logger.error(f"Failed to update source error status: {e}")


def _mark_minute_failed(db, minute_id: str, error: str):
    from app.models.minute import Minute
    try:
        minute = db.query(Minute).filter(Minute.id == UUID(minute_id)).first()
        if minute:
            minute.processing_status = "failed"
            minute.processing_error = error
            db.commit()
    except Exception as e:
        logger.error(f"Failed to update minute error status: {e}")


# Enqueue helper functions (called from API)
def enqueue_source_processing(source_id: UUID, raw_text: str) -> str:
    """Enqueue source content processing task."""
    result = process_source_task.delay(str(source_id), raw_text)
    logger.info(f"Enqueued source processing: {source_id}, task_id: {result.id}")
    return result.id


def enqueue_minute_processing(minute_id: UUID) -> str:
    """Enqueue minute content processing task."""
    result = process_minute_task.delay(str(minute_id))
    logger.info(f"Enqueued minute processing: {minute_id}, task_id: {result.id}")
    return result.id
```

#### chat.py - チャット処理 (低レイテンシー)

```python
"""Celery tasks for chat processing (low latency)."""

import logging
import asyncio
from uuid import UUID
from typing import Optional, List
from celery import shared_task
from app.celery_app.tasks.base import DatabaseTask

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    base=DatabaseTask,
    name="app.celery_app.tasks.chat.process_message",
    queue="chat",
    time_limit=120,
    soft_time_limit=100,
    max_retries=1,  # チャットは素早く失敗を返す
)
def process_chat_message_task(
    self,
    message_id: str,
    notebook_id: str,
    session_id: Optional[str],
    question: str,
    source_ids: Optional[List[str]],
    use_rag: bool,
    use_formatted_text: bool,
):
    """
    Process chat message with RAG retrieval and LLM response.

    Args:
        message_id: Message UUID string
        notebook_id: Notebook UUID string
        session_id: Optional session UUID string
        question: User's question
        source_ids: Optional list of source IDs to search
        use_rag: Whether to use RAG retrieval
        use_formatted_text: Whether to use formatted source text
    """
    from app.services.chat_processor import process_chat_message_async
    from app.core.config import settings

    logger.info(f"Processing chat message: {message_id}")

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                process_chat_message_async(
                    message_id=UUID(message_id),
                    db_url=settings.DATABASE_URL,
                    notebook_id=UUID(notebook_id),
                    session_id=UUID(session_id) if session_id else None,
                    question=question,
                    source_ids=source_ids,
                    use_rag=use_rag,
                    use_formatted_text=use_formatted_text,
                )
            )
        finally:
            loop.close()

        logger.info(f"Chat message processed: {message_id}")
        return {"status": "completed", "message_id": message_id}

    except Exception as e:
        logger.error(f"Chat processing failed: {e}", exc_info=True)
        # Update message status to failed
        _mark_message_failed(self.db, message_id, str(e))
        return {"status": "failed", "message": str(e)}


def _mark_message_failed(db, message_id: str, error: str):
    from app.models.chat import ChatMessage
    try:
        message = db.query(ChatMessage).filter(
            ChatMessage.id == UUID(message_id)
        ).first()
        if message:
            message.status = "failed"
            message.error_message = error
            db.commit()
    except Exception as e:
        logger.error(f"Failed to update message error status: {e}")


def enqueue_chat_processing(
    message_id: UUID,
    notebook_id: UUID,
    session_id: Optional[UUID],
    question: str,
    source_ids: Optional[List[str]],
    use_rag: bool,
    use_formatted_text: bool,
) -> str:
    """Enqueue chat message processing task."""
    result = process_chat_message_task.delay(
        str(message_id),
        str(notebook_id),
        str(session_id) if session_id else None,
        question,
        source_ids,
        use_rag,
        use_formatted_text,
    )
    logger.info(f"Enqueued chat processing: {message_id}, task_id: {result.id}")
    return result.id
```

### 2.4 docker-compose.yml ワーカー分離

```yaml
# 用途別ワーカー構成

# コンテンツ処理ワーカー (Embedding + LLM)
celery-worker-content:
  build:
    context: ./backend
    dockerfile: Dockerfile
  container_name: notebooklm-celery-content
  restart: unless-stopped
  depends_on:
    postgres:
      condition: service_healthy
    redis:
      condition: service_healthy
  environment:
    # ... (backend と同じ環境変数)
  volumes:
    - upload_data:/app/data/uploads
  command: >
    python -m celery -A app.celery_app.celery:celery_app worker
    --loglevel=info
    --concurrency=2
    -Q content
  networks:
    - notebooklm-network

# LLM タスクワーカー (文書チェック・スライド生成)
celery-worker-llm:
  build:
    context: ./backend
    dockerfile: Dockerfile
  container_name: notebooklm-celery-llm
  restart: unless-stopped
  depends_on:
    postgres:
      condition: service_healthy
    redis:
      condition: service_healthy
  environment:
    # ... (backend と同じ環境変数)
  volumes:
    - generated_data:/app/data/generated
  command: >
    python -m celery -A app.celery_app.celery:celery_app worker
    --loglevel=info
    --concurrency=2
    -Q llm
  networks:
    - notebooklm-network

# チャットワーカー (低レイテンシー重視)
celery-worker-chat:
  build:
    context: ./backend
    dockerfile: Dockerfile
  container_name: notebooklm-celery-chat
  restart: unless-stopped
  depends_on:
    postgres:
      condition: service_healthy
    redis:
      condition: service_healthy
  environment:
    # ... (backend と同じ環境変数)
  volumes:
    - upload_data:/app/data/uploads
  command: >
    python -m celery -A app.celery_app.celery:celery_app worker
    --loglevel=info
    --concurrency=4
    -Q chat
  networks:
    - notebooklm-network

# 文字起こしワーカー (長時間タスク専用)
celery-worker-transcription:
  build:
    context: ./backend
    dockerfile: Dockerfile
  container_name: notebooklm-celery-transcription
  restart: unless-stopped
  depends_on:
    postgres:
      condition: service_healthy
    redis:
      condition: service_healthy
  environment:
    # ... (backend と同じ環境変数)
    WHISPER_SERVER_URL: ${WHISPER_SERVER_URL}
  volumes:
    - audio_temp:/app/data/audio_temp
  command: >
    python -m celery -A app.celery_app.celery:celery_app worker
    --loglevel=info
    --concurrency=1
    -Q transcription
  networks:
    - notebooklm-network
```

---

## Phase 3: 議会関連タスク移行

### 3.1 council.py 実装

```python
"""Celery tasks for council-related processing."""

# process_agenda_content_task
# process_agenda_materials_task
# process_agenda_minutes_task
# regenerate_agenda_summary_task
```

---

## Phase 4: 残りのタスク移行

### 4.1 document.py - 文書チェック
### 4.2 slide.py - スライド生成

---

## 移行手順チェックリスト

### Phase 2: コンテンツ処理 (優先度: 高)

- [ ] `backend/app/celery_app/tasks/content.py` 作成
- [ ] `backend/app/api/v1/sources.py` 修正
- [ ] `backend/app/api/v1/minutes.py` 修正
- [ ] `backend/app/api/v1/processing.py` 修正
- [ ] `backend/app/celery_app/tasks/base.py` にリカバリー関数追加
- [ ] テスト実行

### Phase 3: 議会関連 (優先度: 中)

- [ ] `backend/app/celery_app/tasks/council.py` 作成
- [ ] `backend/app/api/v1/council_agendas.py` 修正
- [ ] テスト実行

### Phase 4: LLM タスク (優先度: 高)

- [ ] `backend/app/celery_app/tasks/document.py` 作成
- [ ] `backend/app/celery_app/tasks/slide.py` 作成
- [ ] `backend/app/api/v1/document_checker.py` 修正
- [ ] `backend/app/api/v1/slide_generator.py` 修正
- [ ] テスト実行

### Phase 5: チャット処理 (優先度: 最高)

- [ ] `backend/app/celery_app/tasks/chat.py` 作成
- [ ] `backend/app/api/v1/chat.py` 修正
- [ ] フロントエンドのポーリング動作確認
- [ ] テスト実行

### Phase 6: docker-compose 最適化

- [ ] ワーカー分離構成の実装
- [ ] リソース制限設定
- [ ] ヘルスチェック追加

---

## リカバリー機能拡張

### base.py 更新

```python
# backend/app/celery_app/tasks/base.py

def recover_all_processing_tasks():
    """Recover all stuck tasks on worker startup."""
    # ...existing transcription recovery...

    # Source recovery
    recovered += recover_source_tasks(db)

    # Minute recovery
    recovered += recover_minute_tasks(db)

    # Agenda recovery
    recovered += recover_agenda_tasks(db)

    # Document check recovery
    recovered += recover_document_check_tasks(db)

    # Slide generation recovery
    recovered += recover_slide_tasks(db)

    # Chat message recovery
    recovered += recover_chat_tasks(db)


def recover_source_tasks(db: Session) -> int:
    """Recover stuck source processing tasks."""
    from app.models.source import Source
    from app.celery_app.tasks.content import process_source_task

    stuck = db.query(Source).filter(
        Source.processing_status == "processing"
    ).all()

    for source in stuck:
        source.processing_status = "pending"
        db.commit()
        # Note: raw_text needs to be re-extracted or stored
        # For now, mark as failed if text not available
        if source.raw_text:
            process_source_task.delay(str(source.id), source.raw_text)
        else:
            source.processing_status = "failed"
            source.processing_error = "Recovery failed: raw_text not available"
            db.commit()

    return len(stuck)
```

---

## モニタリング強化

### Flower ダッシュボード

- タスク成功/失敗率
- キュー別待機数
- ワーカー稼働状況

### アラート設定 (将来)

```python
# タスク失敗時の通知
@celery_app.task(bind=True)
def on_task_failure(self, exc, task_id, args, kwargs, einfo):
    """Handle task failure notification."""
    logger.error(f"Task {task_id} failed: {exc}")
    # Slack/Email notification (future)
```

---

## 推定工数

| Phase | 内容 | 工数 |
|-------|------|------|
| Phase 2 | コンテンツ処理移行 | 4-6時間 |
| Phase 3 | 議会関連移行 | 3-4時間 |
| Phase 4 | LLMタスク移行 | 3-4時間 |
| Phase 5 | チャット処理移行 | 2-3時間 |
| Phase 6 | docker-compose最適化 | 2-3時間 |
| **合計** | | **14-20時間** |

---

## 注意事項

1. **チャット処理は最後に移行**: ユーザー体験への影響が大きいため、十分なテストが必要
2. **raw_text の永続化**: Source のリカバリーには raw_text が必要。現在は保存していない場合がある
3. **LLM タイムアウト**: LLM の応答が遅い場合、タスクタイムアウトに注意
4. **並行処理制限**: LLM API への同時リクエスト数を考慮した concurrency 設定
