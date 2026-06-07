import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, DateTime, Enum, Text, JSON, Float, ForeignKey
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    REVOKED = "revoked"


class JobType(str, enum.Enum):
    EMAIL = "email"
    IMAGE_RESIZE = "image_resize"
    REPORT = "report"


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True)           # Celery task ID
    type = Column(Enum(JobType), nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False)
    priority = Column(Integer, default=5)           # 1 (highest) – 10 (lowest)
    payload = Column(JSON, nullable=False)           # task input data
    result = Column(JSON, nullable=True)             # task output / error
    progress = Column(Float, default=0.0)            # 0.0 – 100.0
    queue = Column(String, nullable=False)
    worker_id = Column(String, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    queued_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Computed duration in seconds
    @property
    def duration_seconds(self):
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "status": self.status,
            "priority": self.priority,
            "payload": self.payload,
            "result": self.result,
            "progress": self.progress,
            "queue": self.queue,
            "worker_id": self.worker_id,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "queued_at": self.queued_at.isoformat() if self.queued_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
        }
