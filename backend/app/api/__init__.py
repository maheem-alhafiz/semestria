"""Aggregates all versioned API routers into one router main.py mounts."""

from fastapi import APIRouter

from app.api.academic_record import router as academic_record_router
from app.api.courses import router as courses_router
from app.api.plans import router as plans_router
from app.api.schedules import router as schedules_router
from app.api.terms import router as terms_router

api_router = APIRouter()
api_router.include_router(terms_router)
api_router.include_router(courses_router)
api_router.include_router(schedules_router)
api_router.include_router(plans_router)
api_router.include_router(academic_record_router)

__all__ = ["api_router"]
