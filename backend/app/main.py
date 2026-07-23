"""
FastAPI application entrypoint.

Mounts the versioned API router (terms, courses, schedules) under
settings.api_v1_prefix, alongside a plain health check.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="UManitoba Course Planner API",
    version="0.1.0",
    description="Backend for the Coursicle-inspired UManitoba academic planner.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Basic liveness/readiness probe."""
    return {"status": "ok", "environment": settings.app_env}
