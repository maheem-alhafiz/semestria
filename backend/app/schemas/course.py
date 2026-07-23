from pydantic import BaseModel, ConfigDict


class CourseRead(BaseModel):
    """Full course record, returned from course search."""

    model_config = ConfigDict(from_attributes=True)

    course_id: int
    subject: str
    course_number: str
    title: str
    credit_hours: float


class CourseBrief(BaseModel):
    """Lightweight course reference nested inside a SectionRead -- avoids
    re-sending the full course record for every section in a schedule."""

    model_config = ConfigDict(from_attributes=True)

    subject: str
    course_number: str
    title: str
