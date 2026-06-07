"""
Email Worker
============
Simulates sending emails (SMTP / SendGrid / SES in production).
Demonstrates: retries, progress updates, dead-letter handling.
"""
import time
import random
import logging
from datetime import datetime
from celery import Task
from celery.utils.log import get_task_logger
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.job import Job, JobStatus

logger = get_task_logger(__name__)


class CallbackTask(Task):
    """Base task that writes status back to PostgreSQL."""

    def on_success(self, retval, task_id, args, kwargs):
        _update_job(task_id, JobStatus.SUCCESS, result=retval, progress=100.0)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        _update_job(
            task_id,
            JobStatus.FAILED,
            error_message=str(exc),
        )

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        _update_job(task_id, JobStatus.RETRYING, error_message=str(exc))


def _update_job(task_id: str, status: JobStatus, **kwargs):
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == task_id).first()
        if job:
            job.status = status
            if "result" in kwargs:
                job.result = kwargs["result"]
            if "error_message" in kwargs:
                job.error_message = kwargs["error_message"]
            if "progress" in kwargs:
                job.progress = kwargs["progress"]
            if status == JobStatus.SUCCESS:
                job.completed_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


@celery_app.task(
    bind=True,
    base=CallbackTask,
    name="app.workers.email_worker.send_email",
    queue="email",
    max_retries=3,
    default_retry_delay=30,
    soft_time_limit=60,
    time_limit=90,
)
def send_email(self, job_id: str, to: str, subject: str, body: str):
    """
    Simulate sending an email.
    - Updates progress at each stage
    - Randomly fails 10% of the time to demonstrate retry logic
    """
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = JobStatus.RUNNING
            job.started_at = datetime.utcnow()
            job.worker_id = self.request.hostname
            job.progress = 10.0
            db.commit()

        logger.info(f"[EMAIL] Connecting to SMTP for job {job_id}")
        time.sleep(0.5)  # simulate SMTP connect

        if job:
            job.progress = 40.0
            db.commit()

        # Simulate occasional failure (10%)
        if random.random() < 0.10:
            raise ConnectionError("SMTP connection refused (simulated)")

        logger.info(f"[EMAIL] Sending to {to}: {subject}")
        time.sleep(random.uniform(0.5, 1.5))  # simulate send latency

        if job:
            job.progress = 80.0
            db.commit()

        time.sleep(0.3)  # simulate acknowledgment
        logger.info(f"[EMAIL] Delivered to {to}")

        return {
            "delivered_to": to,
            "subject": subject,
            "message_id": f"msg_{job_id[:8]}@taskforge.local",
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as exc:
        logger.warning(f"[EMAIL] Failed job {job_id}: {exc}. Retrying...")
        if job:
            job.retry_count += 1
            db.commit()
        raise self.retry(exc=exc)

    finally:
        db.close()
