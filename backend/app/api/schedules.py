from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas import ScheduleGenerateRequest, ScheduleGenerateResponse
from app.services.scheduler import generate_schedules

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.post("/generate", response_model=ScheduleGenerateResponse)
def generate(request: ScheduleGenerateRequest, db: Session = Depends(get_db)) -> dict:
    """
    Run the constraint-satisfaction engine for the given term + desired
    courses and return every valid, conflict-free schedule.

    `locked_crns` (optional) narrows generation to only combinations
    consistent with sections the student explicitly picked via the
    frontend's per-slot picker -- see app.services.scheduler's docstring
    for exactly how a course's candidate bundles get filtered by these.

    An empty `schedules` list is a valid response, not an error: it means
    no combination of sections satisfies every constraint (e.g. two
    courses whose only sections always overlap, or a locked CRN that
    conflicts with another course's only option).
    """
    schedules = generate_schedules(
        db,
        term_code=request.term_code,
        course_ids=request.course_ids,
        max_results=request.max_results,
        locked_crns=request.locked_crns,
    )
    return {
        "schedule_count": len(schedules),
        "schedules": [{"sections": s.sections} for s in schedules],
    }
