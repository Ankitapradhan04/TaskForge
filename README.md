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
