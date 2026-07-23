from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.models import Course, Section
from app.schemas import CourseRead
from app.schemas.section_groups import (
    CourseSectionsRead,
    SectionGroupRead,
    SectionOptionRead,
    SectionSlotRead,
)

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("", response_model=list[CourseRead])
def search_courses(
    term_code: str = Query(..., description="Only courses with at least one section in this term"),
    q: str | None = Query(
        default=None,
        description="Free-text match on subject, course number, or title, e.g. 'MECH' or 'Thermo'",
    ),
    db: Session = Depends(get_db),
) -> list[Course]:
    """Search the catalog. `term_code` is required since a course with no
    sections in that term can't be scheduled anyway. `q` is optional."""
    stmt = (
        select(Course)
        .join(Section, Section.course_id == Course.course_id)
        .where(Section.term_code == term_code)
    )

    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            or_(
                Course.subject.ilike(pattern),
                Course.course_number.ilike(pattern),
                Course.title.ilike(pattern),
                # Matches a combined subject+number query against both the
                # space-separated form ("MECH 2222") and the concatenated
                # form ("MECH2222") -- individual-column checks above never
                # match a query spanning both columns.
                func.concat(Course.subject, " ", Course.course_number).ilike(pattern),
                func.concat(Course.subject, Course.course_number).ilike(pattern),
            )
        )

    stmt = stmt.distinct().order_by(Course.subject, Course.course_number)
    return db.execute(stmt).scalars().all()


@router.get("/{course_id}/sections", response_model=CourseSectionsRead)
def get_course_sections(
    course_id: int,
    term_code: str = Query(..., description="Which term's sections to return"),
    db: Session = Depends(get_db),
) -> CourseSectionsRead:
    """
    Sections for one course in one term, pre-grouped by link_group_id and
    link_slot so the frontend can render "pick one of these labs" style
    pickers directly, without re-deriving Aurora's linking convention
    itself -- see app.schemas.section_groups for the exact shape and
    app.importer.link_resolver for how link_group_id/link_slot are set.
    """
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail=f"Course {course_id} not found")

    stmt = (
        select(Section)
        .options(selectinload(Section.meeting_times))
        .where(Section.course_id == course_id, Section.term_code == term_code)
        .order_by(Section.section_number)
    )
    sections = db.execute(stmt).scalars().all()

    # Real link groups: keyed by link_group_id, sub-keyed by link_slot.
    linked_groups: dict[int, dict[str, list[Section]]] = defaultdict(lambda: defaultdict(list))
    # Standalone sections (link_group_id is None) each become their own
    # synthetic single-slot, single-option group -- so the frontend can
    # treat every course uniformly instead of special-casing "no group".
    standalone: list[Section] = []

    for section in sections:
        if section.link_group_id is None:
            standalone.append(section)
        else:
            slot = section.link_slot or "SECTION"
            linked_groups[section.link_group_id][slot].append(section)

    def to_option(section: Section) -> SectionOptionRead:
        return SectionOptionRead.model_validate(section)

    groups: list[SectionGroupRead] = [
        SectionGroupRead(
            link_group_id=link_group_id,
            slots=[
                SectionSlotRead(link_slot=slot, options=[to_option(s) for s in members])
                for slot, members in slots_by_name.items()
            ],
        )
        for link_group_id, slots_by_name in linked_groups.items()
    ]

    """
    OLD CODE
    for section in standalone:
        groups.append(
            SectionGroupRead(
                link_group_id=None,
                slots=[
                    SectionSlotRead(
                        link_slot=section.link_slot or "SECTION",
                        options=[to_option(section)],
                    )
                ],
            )
        )

    return CourseSectionsRead(
        course_id=course.course_id,
        subject=course.subject,
        course_number=course.course_number,
        title=course.title,
        credit_hours=float(course.credit_hours),
        groups=groups,
    )"""

    #NEW code
    if standalone:
        # Group standalone sections by their slot name (usually "SECTION")
        # so they populate a single dropdown instead of separate mandatory boxes.
        standalone_slots = defaultdict(list)
        for section in standalone:
            slot_name = section.link_slot or "SECTION"
            standalone_slots[slot_name].append(to_option(section))

        groups.append(
            SectionGroupRead(
                link_group_id=None,
                slots=[
                    SectionSlotRead(link_slot=slot_name, options=options)
                    for slot_name, options in standalone_slots.items()
                ],
            )
        )

    return CourseSectionsRead(
        course_id=course.course_id,
        subject=course.subject,
        course_number=course.course_number,
        title=course.title,
        credit_hours=float(course.credit_hours),
        groups=groups,
    )
