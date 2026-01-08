"""
Celery tasks package.

This package contains task definitions for various background operations:
- transcription: YouTube video transcription tasks
- content: Source and minute processing tasks
- council: Council agenda processing tasks
- document: Document checking tasks
- slide: Slide generation tasks
- chat: Chat message processing tasks
"""

from app.celery_app.tasks.base import recover_all_processing_tasks
from app.celery_app.tasks.transcription import process_transcription_task
from app.celery_app.tasks.content import process_source_task, process_minute_task
from app.celery_app.tasks.council import (
    process_agenda_content_task,
    process_agenda_materials_task,
    process_agenda_minutes_task,
    regenerate_agenda_summary_task,
)
from app.celery_app.tasks.document import process_document_check_task
from app.celery_app.tasks.slide import process_slide_generation_task
from app.celery_app.tasks.chat import process_chat_message_task

__all__ = [
    # Base
    "recover_all_processing_tasks",
    # Transcription
    "process_transcription_task",
    # Content
    "process_source_task",
    "process_minute_task",
    # Council
    "process_agenda_content_task",
    "process_agenda_materials_task",
    "process_agenda_minutes_task",
    "regenerate_agenda_summary_task",
    # Document
    "process_document_check_task",
    # Slide
    "process_slide_generation_task",
    # Chat
    "process_chat_message_task",
]
