"""
Jobs API
========
POST /jobs/email         – enqueue an email send
POST /jobs/image-resize  – enqueue an image resize
POST /jobs/report        – enqueue a report generation
GET  /jobs               – list all jobs (filterable)
GET  /jobs/{id}          – get job detail + live status
DELETE /jobs/{id}        – revoke (cancel) a queued/running job
GET  /jobs/stats         – system-wide queue statistics
"""
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.core.database import get_db
from app.models.job import Job, JobStatus, JobType
from app.schemas.job import (
    EmailJobRequest,
    ImageResizeJobRequest,
    ReportJobRequest,
    JobResponse,
    JobListResponse,
    SystemStats,
    QueueStats,
)
from app.workers.email_worker import send_email
from app.workers.image_worker import resize_image
from app.workers.report_worker import generate_report
from app.core.celery_app import celery_app

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _create_job(db: Session, job_id: str, job_type: JobType, queue: str, payload: dict, priority: int) -> Job:
    job = Job(
        id=job_id,
        type=job_type,
        status=JobStatus.QUEUED,
        queue=queue,
        payload=payload,
        priority=priority,
        queued_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


# ── Enqueue endpoints ────────────────────────────────────────────────────────

@router.post("/email", response_model=JobResponse, status_code=202)
def enqueue_email(req: EmailJobRequest, db: Session = Depends(get_db)):
    job_id = str(uuid.uuid4())
    payload = {"to": req.to, "subject": req.subject, "body": req.body}
    job = _create_job(db, job_id, JobType.EMAIL, "email", payload, req.priority)

    send_email.apply_async(
        kwargs={"job_id": job_id, "to": req.to, "subject": req.subject, "body": req.body},
        task_id=job_id,
        priority=req.priority,
        queue="email",
    )
    return job.to_dict()


@router.post("/image-resize", response_model=JobResponse, status_code=202)
def enqueue_image_resize(req: ImageResizeJobRequest, db: Session = Depends(get_db)):
    job_id = str(uuid.uuid4())
    payload = {
        "image_url": req.image_url,
        "width": req.width,
        "height": req.height,
        "format": req.format,
    }
    job = _create_job(db, job_id, JobType.IMAGE_RESIZE, "images", payload, req.priority)

    resize_image.apply_async(
        kwargs={
            "job_id": job_id,
            "image_url": req.image_url,
            "width": req.width,
            "height": req.height,
            "output_format": req.format,
        },
        task_id=job_id,
        priority=req.priority,
        queue="images",
    )
    return job.to_dict()


@router.post("/report", response_model=JobResponse, status_code=202)
def enqueue_report(req: ReportJobRequest, db: Session = Depends(get_db)):
    job_id = str(uuid.uuid4())
    payload = {"report_type": req.report_type, "parameters": req.parameters}
    job = _create_job(db, job_id, JobType.REPORT, "reports", payload, req.priority)

    generate_report.apply_async(
        kwargs={
            "job_id": job_id,
            "report_type": req.report_type,
            "parameters": req.parameters,
        },
        task_id=job_id,
        priority=req.priority,
        queue="reports",
    )
    return job.to_dict()


# ── Query endpoints ──────────────────────────────────────────────────────────

@router.get("", response_model=JobListResponse)
def list_jobs(
    db: Session = Depends(get_db),
    status: Optional[JobStatus] = None,
    job_type: Optional[JobType] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    q = db.query(Job)
    if status:
        q = q.filter(Job.status == status)
    if job_type:
        q = q.filter(Job.type == job_type)
    total = q.count()
    jobs = q.order_by(Job.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"jobs": [j.to_dict() for j in jobs], "total": total, "page": page, "page_size": page_size}


@router.get("/stats", response_model=SystemStats)
def get_stats(db: Session = Depends(get_db)):
    queue_names = ["email", "images", "reports"]
    stats = []
    for q_name in queue_names:
        rows = (
            db.query(Job.status, func.count(Job.id))
            .filter(Job.queue == q_name)
            .group_by(Job.status)
            .all()
        )
        counts = {r[0]: r[1] for r in rows}
        stats.append(QueueStats(
            queue=q_name,
            pending=counts.get(JobStatus.PENDING, 0) + counts.get(JobStatus.QUEUED, 0),
            running=counts.get(JobStatus.RUNNING, 0) + counts.get(JobStatus.RETRYING, 0),
            success=counts.get(JobStatus.SUCCESS, 0),
            failed=counts.get(JobStatus.FAILED, 0),
            total=sum(counts.values()),
        ))

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    total_today = db.query(Job).filter(Job.created_at >= today_start).count()

    avg_result = db.query(func.avg(
        func.extract("epoch", Job.completed_at) - func.extract("epoch", Job.started_at)
    )).filter(Job.status == JobStatus.SUCCESS, Job.started_at.isnot(None), Job.completed_at.isnot(None)).scalar()

    # Check Celery workers via inspect
    inspect = celery_app.control.inspect(timeout=1.0)
    active = inspect.active() or {}
    workers_online = len(active)

    return SystemStats(
        queues=stats,
        workers_online=workers_online,
        total_jobs_today=total_today,
        avg_duration_seconds=round(float(avg_result), 2) if avg_result else None,
    )


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_dict()


@router.delete("/{job_id}", status_code=204)
def revoke_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status in (JobStatus.SUCCESS, JobStatus.FAILED):
        raise HTTPException(status_code=400, detail="Cannot revoke a completed job")

    celery_app.control.revoke(job_id, terminate=True, signal="SIGTERM")
    job.status = JobStatus.REVOKED
    job.completed_at = datetime.utcnow()
    db.commit()
