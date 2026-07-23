"""
Importing this package guarantees every model has been registered on
Base.metadata -- required for Alembic's `--autogenerate` to see the full
schema. Alembic's env.py imports `app.models` (not individual model files)
for exactly this reason.
"""

from app.core.database import Base
from app.models.academic_record import AcademicRecord
from app.models.course import Course
from app.models.link_group import LinkGroup
from app.models.meeting_time import MeetingTime
from app.models.plan import Plan
from app.models.plan_item import PlanItem, PlanItemSection
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
]
