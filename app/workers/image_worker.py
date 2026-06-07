"""
Image Resize Worker
===================
Downloads an image from a URL, resizes it using Pillow, and stores metadata.
Demonstrates: CPU-bound task isolation, progress streaming, file handling.
"""
import io
import time
import random
import logging
from datetime import datetime
from celery.utils.log import get_task_logger
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.job import Job, JobStatus

logger = get_task_logger(__name__)


def _set_progress(db, job, pct: float):
    if job:
        job.progress = pct
        db.commit()


@celery_app.task(
    bind=True,
    name="app.workers.image_worker.resize_image",
    queue="images",
    max_retries=2,
    default_retry_delay=10,
    soft_time_limit=120,
    time_limit=150,
)
def resize_image(
    self,
    job_id: str,
    image_url: str,
    width: int,
    height: int,
    output_format: str = "JPEG",
):
    """
    Resize an image to the given dimensions.
    Uses Pillow. In production, output would be uploaded to S3/GCS.
    """
    db = SessionLocal()
    job = None
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = JobStatus.RUNNING
            job.started_at = datetime.utcnow()
            job.worker_id = self.request.hostname
            db.commit()

        logger.info(f"[IMG] Downloading {image_url}")
        _set_progress(db, job, 20.0)

        # --- Simulate download (real: httpx.get(image_url)) ---
        time.sleep(random.uniform(0.4, 1.0))

        if random.random() < 0.07:
            raise ValueError(f"Failed to fetch image from {image_url} (simulated 404)")

        _set_progress(db, job, 50.0)

        # --- Simulate Pillow resize ---
        logger.info(f"[IMG] Resizing to {width}x{height} as {output_format}")
        time.sleep(random.uniform(0.3, 0.8))

        _set_progress(db, job, 80.0)

        # --- Simulate upload to object storage ---
        logger.info(f"[IMG] Uploading result to storage")
        time.sleep(0.3)

        output_key = f"resized/{job_id[:8]}_{width}x{height}.{output_format.lower()}"

        result = {
            "original_url": image_url,
            "output_key": output_key,
            "output_url": f"https://cdn.taskforge.local/{output_key}",
            "width": width,
            "height": height,
            "format": output_format,
            "size_bytes": random.randint(10_000, 500_000),
            "processed_at": datetime.utcnow().isoformat(),
        }

        if job:
            job.status = JobStatus.SUCCESS
            job.result = result
            job.progress = 100.0
            job.completed_at = datetime.utcnow()
            db.commit()

        logger.info(f"[IMG] Done: {output_key}")
        return result

    except Exception as exc:
        logger.warning(f"[IMG] Job {job_id} failed: {exc}")
        if job:
            job.retry_count += 1
            db.commit()

        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=10)

        if job:
            job.status = JobStatus.FAILED
            job.error_message = str(exc)
            job.completed_at = datetime.utcnow()
            db.commit()
        raise

    finally:
        db.close()
