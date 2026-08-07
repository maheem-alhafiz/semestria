from app.core.database import Base
from app.models.academic_record import AcademicRecord
from app.models.assessment import (
    Assessment,
    GradeScaleCutoff,
    Todo,
    TrackedCourse,
    WeeklyTopic,
)
from app.models.course import Course
from app.models.course_relationship import CourseRelationship
from app.models.degree_program import DegreeProgram, DegreeProgramInclude
from app.models.link_group import LinkGroup
from app.models.manual_fulfillment import ManualRequirementFulfillment
from app.models.meeting_time import MeetingTime
from app.models.plan import Plan
from app.models.plan_item import PlanItem, PlanItemSection
from app.models.requirement_group import (
    RequirementGroup,
    RequirementGroupCourse,
    RequirementGroupPattern,
)
from app.models.section import Section
from app.models.term import Term

__all__ = [
    "Base",
    "Term",
    "Course",
    "Section",
    "MeetingTime",
    "LinkGroup",
    "Plan",
    "PlanItem",
    "PlanItemSection",
    "AcademicRecord",
    "DegreeProgram",
    "DegreeProgramInclude",
    "RequirementGroup",
    "RequirementGroupCourse",
    "RequirementGroupPattern",
    "CourseRelationship",
    "ManualRequirementFulfillment",
    "Assessment",
    "WeeklyTopic",
    "TrackedCourse",
    "Todo",
    "GradeScaleCutoff",
]
