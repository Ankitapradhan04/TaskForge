#!/bin/bash
# start.sh — Starts all TaskForge processes locally (without Docker)
# Requires: Redis + Postgres running, venv activated

set -e
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  TaskForge Local Dev Launcher"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Kill background jobs on exit
trap "kill 0" EXIT

# Start API
echo "▶ Starting FastAPI..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &

sleep 1

# Start workers
echo "▶ Starting email worker..."
celery -A app.core.celery_app.celery_app worker --queues=email --concurrency=4 --hostname=email@%h --loglevel=info &

echo "▶ Starting image worker..."
celery -A app.core.celery_app.celery_app worker --queues=images --concurrency=2 --hostname=images@%h --loglevel=info &

echo "▶ Starting report worker..."
celery -A app.core.celery_app.celery_app worker --queues=reports --concurrency=2 --hostname=reports@%h --loglevel=info &

echo "▶ Starting Celery Beat (scheduler)..."
celery -A app.core.celery_app.celery_app beat --loglevel=info &

echo "▶ Starting Flower (monitoring UI)..."
celery -A app.core.celery_app.celery_app flower --port=5555 &

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✓ API       → http://localhost:8000"
echo "  ✓ API Docs  → http://localhost:8000/docs"
echo "  ✓ Flower    → http://localhost:5555"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Press Ctrl+C to stop all processes."

wait
