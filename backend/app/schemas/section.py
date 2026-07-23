from datetime import time

from pydantic import BaseModel, ConfigDict

from app.schemas.course import CourseBrief


class MeetingTimeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    meeting_type: str
    start_time: time | None
    end_time: time | None
    monday: bool
    tuesday: bool
    wednesday: bool
    thursday: bool
    friday: bool
    saturday: bool
    sunday: bool


class SectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    crn: str
    section_number: str
    seats_available: int
    max_enrollment: int | None
    enrollment: int | None
    instructor: str | None
    course: CourseBrief
    meeting_times: list[MeetingTimeRead]
