from celery import Celery
from app.core.config import get_settings

settings = get_settings()


def create_celery_app() -> Celery:
    celery = Celery(
        "taskforge",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
        include=[
            "app.workers.email_worker",
            "app.workers.image_worker",
            "app.workers.report_worker",
        ],
    )

    celery.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        # Routing: different queues for different task types
        task_routes={
            "app.workers.email_worker.*": {"queue": "email"},
            "app.workers.image_worker.*": {"queue": "images"},
            "app.workers.report_worker.*": {"queue": "reports"},
        },
        task_queues={
            "email": {"exchange": "email", "routing_key": "email"},
            "images": {"exchange": "images", "routing_key": "images"},
            "reports": {"exchange": "reports", "routing_key": "reports"},
        },
        # Retry policy
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
        # Result expiry: 24h
        result_expires=86400,
        # Beat schedule for periodic tasks
        beat_schedule={
            "cleanup-old-jobs": {
                "task": "app.workers.report_worker.cleanup_old_jobs",
                "schedule": 3600.0,  # every hour
            },
        },
    )
    return celery


celery_app = create_celery_app()
