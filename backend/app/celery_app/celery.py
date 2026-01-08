"""
Celery application initialization.

This module creates and configures the Celery app instance,
sets up task autodiscovery, and provides startup recovery hooks.
"""

import logging
from celery import Celery
from celery.signals import worker_ready

from app.celery_app.config import CeleryConfig

logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery("notebooklm")

# Load configuration
celery_app.config_from_object(CeleryConfig)

# Auto-discover tasks in the tasks package
celery_app.autodiscover_tasks(
    [
        "app.celery_app.tasks",
    ],
    force=True,
)


@worker_ready.connect
def on_worker_ready(sender, **kwargs):
    """
    Called when a Celery worker is ready to accept tasks.

    This hook recovers any tasks that were interrupted when the
    previous worker instance was stopped (e.g., container restart).
    """
    logger.info("Celery worker ready, checking for interrupted tasks...")

    # Import here to avoid circular imports
    from app.celery_app.tasks.base import recover_processing_tasks

    # Run recovery in a separate task
    celery_app.send_task(
        "app.celery_app.tasks.base.recover_all_processing_tasks",
    )
