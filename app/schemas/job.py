from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, Any, Dict, List
from datetime import datetime
from app.models.job import JobStatus, JobType


# ── Request Schemas ──────────────────────────────────────────────────────────

class EmailJobRequest(BaseModel):
    to: str
    subject: str
    body: str
    priority: int = 5

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v):
        if not 1 <= v <= 10:
            raise ValueError("priority must be between 1 and 10")
        return v


class ImageResizeJobRequest(BaseModel):
    image_url: str
    width: int
    height: int
    format: str = "JPEG"
    priority: int = 5

    @field_validator("width", "height")
    @classmethod
    def validate_dimensions(cls, v):
        if v <= 0 or v > 8000:
            raise ValueError("dimension must be between 1 and 8000")
        return v

    @field_validator("format")
    @classmethod
    def validate_format(cls, v):
        allowed = {"JPEG", "PNG", "WEBP"}
        if v.upper() not in allowed:
            raise ValueError(f"format must be one of {allowed}")
        return v.upper()


class ReportJobRequest(BaseModel):
    report_type: str           # e.g. "monthly_sales", "user_activity"
    parameters: Dict[str, Any] = {}
    priority: int = 5


# ── Response Schemas ─────────────────────────────────────────────────────────

class JobResponse(BaseModel):
    id: str
    type: JobType
    status: JobStatus
    priority: int
    payload: Dict[str, Any]
    result: Optional[Any] = None
    progress: float
    queue: str
    worker_id: Optional[str] = None
    retry_count: int
    max_retries: int
    error_message: Optional[str] = None
    created_at: datetime
    queued_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    jobs: List[JobResponse]
    total: int
    page: int
    page_size: int


class QueueStats(BaseModel):
    queue: str
    pending: int
    running: int
    success: int
    failed: int
    total: int


class SystemStats(BaseModel):
    queues: List[QueueStats]
    workers_online: int
    total_jobs_today: int
    avg_duration_seconds: Optional[float] = None
