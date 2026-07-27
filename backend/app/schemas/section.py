from datetime import date, time

from pydantic import BaseModel, ConfigDict

from app.schemas.course import CourseBrief


class MeetingTimeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    meeting_type: str
    start_time: time | None
    end_time: time | None
    # Per-meeting date range -- see app.models.meeting_time's docstring.
    # When start_date == end_date, this is a genuine single-occurrence
    # meeting (e.g. one of CHEM 1126's standalone lab dates), not a
    # term-wide recurring one -- the ICS generator uses this to decide
    # whether to emit a plain VEVENT or one with a weekly RRULE.
    start_date: date | None
    end_date: date | None
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
