from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.jobs import router as jobs_router
from app.core.database import engine, Base

# Create all tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="TaskForge",
    description="Distributed Job Queue & Task Worker System — Python + Celery + Redis + PostgreSQL",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs_router)


@app.get("/", tags=["health"])
def root():
    return {
        "service": "TaskForge",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "flower": "http://localhost:5555",
    }


@app.get("/health", tags=["health"])
def health():
    return JSONResponse({"status": "ok"})
