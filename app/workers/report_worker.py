"""
Report Generation Worker
========================
Simulates long-running report generation (SQL aggregation, CSV export, PDF rendering).
Demonstrates: long tasks, granular progress updates, periodic/scheduled tasks.
"""
import time
import random
import json
import logging
from datetime import datetime, timedelta
from celery.utils.log import get_task_logger
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.job import Job, JobStatus

logger = get_task_logger(__name__)

REPORT_STEPS = [
    (15, "Connecting to data warehouse"),
    (30, "Running aggregation queries"),
    (50, "Joining fact tables"),
    (65, "Applying filters and grouping"),
    (78, "Formatting data rows"),
    (88, "Rendering PDF / CSV"),
    (95, "Uploading to storage"),
    (100, "Done"),
]


@celery_app.task(
    bind=True,
    name="app.workers.report_worker.generate_report",
    queue="reports",
    max_retries=1,
    soft_time_limit=300,
    time_limit=360,
)
def generate_report(
    self,
    job_id: str,
    report_type: str,
    parameters: dict,
):
    """
    Simulate a multi-step report generation pipeline.
    Progress updates are written back to PostgreSQL at each stage.
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

        row_count = random.randint(1_000, 500_000)

        for progress_pct, step_label in REPORT_STEPS:
            logger.info(f"[REPORT] {step_label} ({progress_pct}%)")
            time.sleep(random.uniform(0.3, 0.9))

            if random.random() < 0.05 and progress_pct < 80:
                raise RuntimeError(f"Query timeout during: {step_label} (simulated)")

            if job:
                job.progress = float(progress_pct)
                db.commit()

        report_key = f"reports/{report_type}/{job_id[:8]}.pdf"
        result = {
            "report_type": report_type,
            "parameters": parameters,
            "row_count": row_count,
            "output_key": report_key,
            "download_url": f"https://reports.taskforge.local/{report_key}",
            "generated_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat(),
        }

        if job:
            job.status = JobStatus.SUCCESS
            job.result = result
            job.completed_at = datetime.utcnow()
            db.commit()

        logger.info(f"[REPORT] Completed {report_type}: {row_count} rows")
        return result

    except Exception as exc:
        logger.error(f"[REPORT] Job {job_id} failed: {exc}")
        if job:
            job.status = JobStatus.FAILED
            job.error_message = str(exc)
            job.completed_at = datetime.utcnow()
            db.commit()
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=30)
        raise

    finally:
        db.close()


@celery_app.task(name="app.workers.report_worker.cleanup_old_jobs")
def cleanup_old_jobs():
    """
    Periodic task (runs every hour via Celery Beat).
    Deletes completed/failed jobs older than 7 days.
    """
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=7)
        deleted = (
            db.query(Job)
            .filter(
                Job.status.in_([JobStatus.SUCCESS, JobStatus.FAILED]),
                Job.completed_at < cutoff,
            )
            .delete(synchronize_session=False)
        )
        db.commit()
        logger.info(f"[CLEANUP] Purged {deleted} old jobs")
        return {"deleted": deleted}
    finally:
        db.close()
