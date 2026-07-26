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


class CourseDetailRead(CourseRead):
    """Full detail for the Course Details Modal -- CourseRead plus the
    scraped catalog text. All three text fields are nullable: a course
    the Aurora importer created but the catalog scraper hasn't reached
    yet (or one with genuinely no prerequisites) will have them as None,
    not empty strings -- the frontend should treat that as "not available"
    rather than "confirmed empty"."""

    description: str | None
    prerequisites_text: str | None
    corequisites_text: str | None
