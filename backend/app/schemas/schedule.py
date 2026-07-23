from pydantic import BaseModel, Field

from app.schemas.section import SectionRead


class ScheduleGenerateRequest(BaseModel):
    term_code: str
    course_ids: list[int] = Field(min_length=1)
    max_results: int | None = Field(default=None, ge=1)
    # CRNs the student explicitly picked via the frontend's per-slot
    # picker (e.g. one specific lab out of three) -- narrows generation
    # to only schedules containing all of them. See
    # app.services.scheduler.generate_schedules for how these are applied
    # per-course. Defaults to empty: no picks made yet behaves exactly
    # like the original unconstrained enumeration.
    locked_crns: list[str] = Field(default_factory=list)


class ScheduleRead(BaseModel):
    sections: list[SectionRead]


class ScheduleGenerateResponse(BaseModel):
    schedule_count: int
    schedules: list[ScheduleRead]
