"""
Celery configuration settings.

This module provides configuration values for Celery workers,
including queue definitions, timeouts, and retry settings.
"""

from app.core.config import settings


class CeleryConfig:
    """Celery configuration class."""

    # Broker and backend URLs
    broker_url = settings.celery_broker_url
    result_backend = settings.celery_result_backend

    # Serialization
    task_serializer = "json"
    result_serializer = "json"
    accept_content = ["json"]

    # Timezone
    timezone = "Asia/Tokyo"
    enable_utc = True

    # Task settings
    task_track_started = True
    task_time_limit = 3600  # 1 hour hard limit
    task_soft_time_limit = 3300  # 55 minutes soft limit

    # Result settings
    result_expires = 86400  # 24 hours

    # Worker settings
    worker_prefetch_multiplier = 1  # For long-running tasks
    worker_concurrency = 2  # Default concurrent tasks

    # Task routing - define queues for different task types
    task_routes = {
        # Long-running transcription tasks (dedicated worker recommended)
        "app.celery_app.tasks.transcription.*": {"queue": "transcription"},
        # Content processing (embedding + LLM formatting/summary)
        "app.celery_app.tasks.content.*": {"queue": "content"},
        "app.celery_app.tasks.council.*": {"queue": "content"},
        # LLM-intensive tasks (document checking, slide generation)
        "app.celery_app.tasks.document.*": {"queue": "llm"},
        "app.celery_app.tasks.slide.*": {"queue": "llm"},
        # Low-latency chat processing
        "app.celery_app.tasks.chat.*": {"queue": "chat"},
    }

    # Default queue
    task_default_queue = "default"

    # Queue definitions
    task_queues = None  # Use default queue configuration

    # Retry settings
    task_acks_late = True  # Acknowledge after task completion
    task_reject_on_worker_lost = True  # Requeue if worker dies


# Retry configuration for tasks
RETRY_CONFIG = {
    "max_retries": 3,
    "retry_backoff": True,  # Exponential backoff
    "retry_backoff_max": 600,  # Max 10 minutes between retries
    "retry_jitter": True,  # Add randomness to backoff
}

# Retryable exceptions
RETRYABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    OSError,
)
