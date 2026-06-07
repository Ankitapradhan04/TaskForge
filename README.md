# TaskForge ⚙️

**Distributed Job Queue & Task Worker System**  
Python · Celery · Redis · PostgreSQL · FastAPI

> Resume signal: *Async processing, distributed systems, message queues, worker isolation*

---

## Architecture

```
┌─────────────┐    HTTP POST     ┌─────────────────┐
│   Client    │ ──────────────▶ │  FastAPI  :8000  │
└─────────────┘                  └────────┬────────┘
                                          │ enqueue
                                          ▼
                                   ┌─────────────┐
                                   │    Redis     │  (broker + result backend)
                                   └──────┬──────┘
                               ┌──────────┼──────────┐
                               ▼          ▼           ▼
                         [email Q]   [images Q]  [reports Q]
                               │          │           │
                         ┌─────▼──┐ ┌────▼───┐ ┌────▼────┐
                         │ Worker │ │ Worker │ │ Worker  │
                         │ Email  │ │ Image  │ │ Report  │
                         └────────┘ └────────┘ └─────────┘
                               │          │           │
                               └──────────┼───────────┘
                                          ▼
                                  ┌──────────────┐
                                  │  PostgreSQL  │  (job state + results)
                                  └──────────────┘
                                          ▲
                                   ┌──────┴──────┐
                                   │ Flower :5555 │  (monitoring UI)
                                   └─────────────┘
```

## Features

| Feature | Detail |
|---|---|
| **3 task types** | Email send, Image resize, Report generation |
| **3 isolated queues** | Separate workers per task type |
| **Priority queuing** | 1–10 priority on every job |
| **Auto-retry** | Configurable backoff per worker |
| **Progress tracking** | 0–100% written back to Postgres |
| **Job lifecycle** | PENDING → QUEUED → RUNNING → SUCCESS/FAILED |
| **Revocation** | Cancel queued/running jobs via API |
| **Periodic tasks** | Celery Beat cleans up stale jobs hourly |
| **Monitoring** | Flower UI + `/jobs/stats` endpoint |

---

## Quick Start

### Option A: Docker Compose (recommended)

```bash
git clone https://github.com/YOUR_USERNAME/taskforge
cd taskforge
cp .env.example .env
docker-compose up --build
```

Services:
- API → http://localhost:8000
- Swagger → http://localhost:8000/docs
- Flower → http://localhost:5555

### Option B: Local dev

```bash
# Prerequisites: Redis + PostgreSQL running locally
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # edit DATABASE_URL / REDIS_URL
./start.sh
```

---

## API Reference

### Enqueue Jobs

```bash
# Send an email
curl -X POST http://localhost:8000/jobs/email \
  -H "Content-Type: application/json" \
  -d '{"to":"han@example.com","subject":"Hello","body":"Test","priority":3}'

# Resize an image
curl -X POST http://localhost:8000/jobs/image-resize \
  -H "Content-Type: application/json" \
  -d '{"image_url":"https://picsum.photos/1920/1080","width":800,"height":600,"format":"WEBP"}'

# Generate a report
curl -X POST http://localhost:8000/jobs/report \
  -H "Content-Type: application/json" \
  -d '{"report_type":"monthly_sales","parameters":{"month":"2024-01"}}'
```

### Query Jobs

```bash
# List all jobs
GET /jobs

# Filter by status or type
GET /jobs?status=failed&job_type=email

# Get a specific job
GET /jobs/{id}

# Queue statistics
GET /jobs/stats

# Revoke a job
DELETE /jobs/{id}
```

### Seed demo data

```bash
python scripts/seed.py --count 30
```

---

## Database Schema

```sql
CREATE TABLE jobs (
  id            TEXT PRIMARY KEY,       -- Celery task ID
  type          TEXT NOT NULL,          -- email | image_resize | report
  status        TEXT NOT NULL,          -- pending | queued | running | success | failed | retrying | revoked
  priority      INT  DEFAULT 5,         -- 1 (high) .. 10 (low)
  payload       JSONB NOT NULL,         -- task input
  result        JSONB,                  -- task output
  progress      FLOAT DEFAULT 0,        -- 0.0 .. 100.0
  queue         TEXT NOT NULL,
  worker_id     TEXT,
  retry_count   INT DEFAULT 0,
  max_retries   INT DEFAULT 3,
  error_message TEXT,
  created_at    TIMESTAMP,
  queued_at     TIMESTAMP,
  started_at    TIMESTAMP,
  completed_at  TIMESTAMP
);
```

---

## Deployment (Render.com)

1. Push to GitHub
2. Go to [render.com](https://render.com) → **New → Blueprint**
3. Connect repo — Render reads `render.yaml` automatically
4. It provisions: PostgreSQL, Redis, API web service, 3 worker services
5. Your live API URL: `https://taskforge-api.onrender.com`

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Tech Stack

- **FastAPI** — REST API, automatic OpenAPI docs
- **Celery** — Distributed task queue, retry logic, scheduling
- **Redis** — Message broker + result backend
- **PostgreSQL** — Persistent job state, queryable history
- **Flower** — Real-time Celery monitoring dashboard
- **Alembic** — Database migrations
- **Pillow** — Image processing (image resize worker)
- **Docker Compose** — Local multi-service orchestration

---

*Built as a portfolio project demonstrating production backend patterns: async task processing, distributed worker architecture, message queue design, and job lifecycle management.*
