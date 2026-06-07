"""
TaskForge Test Suite
====================
Tests for API endpoints and worker task logic.
Run with: pytest tests/ -v
"""
import pytest
import uuid
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.models.job import Job, JobStatus, JobType

# ── In-memory SQLite for testing ─────────────────────────────────────────────
TEST_DB_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


# ── Health ────────────────────────────────────────────────────────────────────

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["service"] == "TaskForge"


# ── Email ─────────────────────────────────────────────────────────────────────

@patch("app.api.jobs.send_email.apply_async")
def test_enqueue_email(mock_apply):
    mock_apply.return_value = MagicMock(id="test-id")
    r = client.post("/jobs/email", json={
        "to": "test@example.com",
        "subject": "Hello",
        "body": "World",
        "priority": 3,
    })
    assert r.status_code == 202
    data = r.json()
    assert data["type"] == "email"
    assert data["status"] == "queued"
    assert data["queue"] == "email"
    assert mock_apply.called


@patch("app.api.jobs.send_email.apply_async")
def test_enqueue_email_invalid_priority(mock_apply):
    r = client.post("/jobs/email", json={
        "to": "a@b.com",
        "subject": "X",
        "body": "Y",
        "priority": 99,  # invalid
    })
    assert r.status_code == 422


# ── Image ─────────────────────────────────────────────────────────────────────

@patch("app.api.jobs.resize_image.apply_async")
def test_enqueue_image_resize(mock_apply):
    r = client.post("/jobs/image-resize", json={
        "image_url": "https://example.com/photo.jpg",
        "width": 800,
        "height": 600,
        "format": "WEBP",
    })
    assert r.status_code == 202
    data = r.json()
    assert data["type"] == "image_resize"
    assert data["queue"] == "images"


@patch("app.api.jobs.resize_image.apply_async")
def test_enqueue_image_invalid_format(mock_apply):
    r = client.post("/jobs/image-resize", json={
        "image_url": "https://example.com/photo.jpg",
        "width": 800,
        "height": 600,
        "format": "BMP",  # not allowed
    })
    assert r.status_code == 422


# ── Report ────────────────────────────────────────────────────────────────────

@patch("app.api.jobs.generate_report.apply_async")
def test_enqueue_report(mock_apply):
    r = client.post("/jobs/report", json={
        "report_type": "monthly_sales",
        "parameters": {"month": "2024-01", "region": "APAC"},
    })
    assert r.status_code == 202
    data = r.json()
    assert data["type"] == "report"
    assert data["queue"] == "reports"


# ── List & Get ────────────────────────────────────────────────────────────────

@patch("app.api.jobs.send_email.apply_async")
def test_list_jobs(mock_apply):
    # Create a few jobs
    for _ in range(3):
        client.post("/jobs/email", json={"to": "a@b.com", "subject": "Hi", "body": "."})
    r = client.get("/jobs")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 3
    assert len(data["jobs"]) == 3


@patch("app.api.jobs.send_email.apply_async")
def test_get_job_by_id(mock_apply):
    r = client.post("/jobs/email", json={"to": "a@b.com", "subject": "Hi", "body": "."})
    job_id = r.json()["id"]
    r2 = client.get(f"/jobs/{job_id}")
    assert r2.status_code == 200
    assert r2.json()["id"] == job_id


def test_get_job_not_found():
    r = client.get(f"/jobs/{uuid.uuid4()}")
    assert r.status_code == 404


# ── Revoke ────────────────────────────────────────────────────────────────────

@patch("app.api.jobs.celery_app.control.revoke")
@patch("app.api.jobs.send_email.apply_async")
def test_revoke_job(mock_apply, mock_revoke):
    r = client.post("/jobs/email", json={"to": "a@b.com", "subject": "Hi", "body": "."})
    job_id = r.json()["id"]
    r2 = client.delete(f"/jobs/{job_id}")
    assert r2.status_code == 204
    assert mock_revoke.called


# ── Worker unit tests ─────────────────────────────────────────────────────────

@patch("app.workers.email_worker.SessionLocal")
def test_email_worker_success(mock_session_cls):
    """Test email worker completes successfully."""
    mock_db = MagicMock()
    mock_job = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = mock_job
    mock_session_cls.return_value = mock_db

    task = MagicMock()
    task.request.hostname = "test-worker"
    task.request.retries = 0
    task.max_retries = 3

    # Patch random to always succeed
    with patch("app.workers.email_worker.random.random", return_value=0.5):
        with patch("app.workers.email_worker.time.sleep"):
            from app.workers.email_worker import send_email as fn
            # Call the underlying function directly (not via Celery)
            result = fn.__wrapped__(
                task, "job-123", "test@example.com", "Hello", "Body"
            )
    assert "delivered_to" in result
    assert result["delivered_to"] == "test@example.com"
