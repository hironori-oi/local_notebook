"""
Celery application package for async task processing.

This package provides:
- Celery app configuration
- Task definitions for background processing
- Recovery mechanisms for interrupted tasks
"""

from app.celery_app.celery import celery_app

__all__ = ["celery_app"]
