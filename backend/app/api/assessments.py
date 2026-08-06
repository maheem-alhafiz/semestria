"""
API for the Assessments tab. See app.models.assessment for the full
reasoning behind the three-table shape.

Every route filters by owner_id (the anonymous visitor cookie -- see
app.core.visitor), same as Plans/AcademicRecord.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.visitor import get_current_owner_id
from app.models import Assessment, Course, Plan, PlanItem, TrackedCourse, WeeklyTopic
from app.schemas.assessment import (
    AssessmentCourseRead,
    AssessmentCreate,
    AssessmentRead,
    AssessmentUpdate,
    TrackedCourseCreate,
    WeeklyTopicRead,
    WeeklyTopicUpsert,
)

router = APIRouter(prefix="/assessments", tags=["assessments"])


def _get_owned_assessment_or_404(db: Session, assessment_id: int, owner_id: str) -> Assessment:
    assessment = db.execute(
        select(Assessment).where(Assessment.id == assessment_id, Assessment.owner_id == owner_id)
    ).scalar_one_or_none()
    if assessment is None:
        raise HTTPException(status_code=404, detail=f"Assessment {assessment_id} not found")
    return assessment


# -- Tracked courses (the course list this tab shows for a term) -----------


@router.get("/courses", response_model=list[AssessmentCourseRead])
def list_tracked_courses(
    term_code: str = Query(...),
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner_id),
) -> list[AssessmentCourseRead]:
    """
    Union of two sources -- see app.models.assessment's docstring on why
    there's no single "tracked courses" table:
      - "plan": every distinct course_id in one of this owner's plan_items
        for this term, across all their Plans.
      - "manual": every course_id explicitly added via POST /courses below.
    """
    plan_course_ids = set(
        db.execute(
            select(PlanItem.course_id)
            .join(Plan, Plan.id == PlanItem.plan_id)
            .where(Plan.owner_id == owner_id, PlanItem.term_code == term_code)
            .distinct()
        ).scalars()
    )
    manual_course_ids = set(
        db.execute(
            select(TrackedCourse.course_id).where(
                TrackedCourse.owner_id == owner_id, TrackedCourse.term_code == term_code
            )
        ).scalars()
    )

    all_ids = plan_course_ids | manual_course_ids
    if not all_ids:
        return []

    courses = db.execute(select(Course).where(Course.course_id.in_(all_ids))).scalars().all()
    return [
        AssessmentCourseRead(
            course_id=c.course_id,
            subject=c.subject,
            course_number=c.course_number,
            title=c.title,
            source="plan" if c.course_id in plan_course_ids else "manual",
        )
        for c in sorted(courses, key=lambda c: (c.subject, c.course_number))
    ]


@router.post("/courses", response_model=AssessmentCourseRead, status_code=201)
def add_tracked_course(
    payload: TrackedCourseCreate,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner_id),
) -> AssessmentCourseRead:
    course = db.get(Course, payload.course_id)
    if course is None:
        raise HTTPException(status_code=404, detail=f"Course {payload.course_id} not found")

    stmt = pg_insert(TrackedCourse).values(
        owner_id=owner_id, term_code=payload.term_code, course_id=payload.course_id
    )
    stmt = stmt.on_conflict_do_nothing(
        index_elements=["owner_id", "term_code", "course_id"]
    )
    db.execute(stmt)
    db.commit()

    return AssessmentCourseRead(
        course_id=course.course_id,
        subject=course.subject,
        course_number=course.course_number,
        title=course.title,
        source="manual",
    )


@router.delete("/courses/{term_code}/{course_id}", status_code=204, response_model=None)
def remove_tracked_course(
    term_code: str,
    course_id: int,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner_id),
) -> None:
    """
    Removes a MANUALLY-added course only. If this course_id is also in
    one of the owner's Plans for this term, it'll keep showing up (see
    list_tracked_courses) -- that's by design, this endpoint has no say
    over Plan membership. Existing Assessment/WeeklyTopic rows for the
    course are left untouched either way.
    """
    db.execute(
        delete(TrackedCourse).where(
            TrackedCourse.owner_id == owner_id,
            TrackedCourse.term_code == term_code,
            TrackedCourse.course_id == course_id,
        )
    )
    db.commit()


# -- Assessments (due-dated items) ------------------------------------------


@router.get("", response_model=list[AssessmentRead])
def list_assessments(
    term_code: str = Query(...),
    course_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner_id),
) -> list[Assessment]:
    stmt = select(Assessment).where(
        Assessment.owner_id == owner_id, Assessment.term_code == term_code
    )
    if course_id is not None:
        stmt = stmt.where(Assessment.course_id == course_id)
    # Nulls last: unscheduled items (no due_date yet) sort after dated ones.
    stmt = stmt.order_by(Assessment.due_date.is_(None), Assessment.due_date, Assessment.title)
    return db.execute(stmt).scalars().all()


@router.post("", response_model=AssessmentRead, status_code=201)
def create_assessment(
    payload: AssessmentCreate,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner_id),
) -> Assessment:
    if db.get(Course, payload.course_id) is None:
        raise HTTPException(status_code=404, detail=f"Course {payload.course_id} not found")

    assessment = Assessment(owner_id=owner_id, **payload.model_dump())
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment


@router.patch("/{assessment_id}", response_model=AssessmentRead)
def update_assessment(
    assessment_id: int,
    payload: AssessmentUpdate,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner_id),
) -> Assessment:
    assessment = _get_owned_assessment_or_404(db, assessment_id, owner_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(assessment, field, value)
    db.commit()
    db.refresh(assessment)
    return assessment


@router.delete("/{assessment_id}", status_code=204, response_model=None)
def delete_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner_id),
) -> None:
    assessment = _get_owned_assessment_or_404(db, assessment_id, owner_id)
    db.delete(assessment)
    db.commit()


# -- Weekly topics ------------------------------------------------------


@router.get("/topics", response_model=list[WeeklyTopicRead])
def list_topics(
    term_code: str = Query(...),
    course_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner_id),
) -> list[WeeklyTopic]:
    stmt = select(WeeklyTopic).where(
        WeeklyTopic.owner_id == owner_id, WeeklyTopic.term_code == term_code
    )
    if course_id is not None:
        stmt = stmt.where(WeeklyTopic.course_id == course_id)
    stmt = stmt.order_by(WeeklyTopic.week_start_date)
    return db.execute(stmt).scalars().all()


@router.put("/topics", response_model=WeeklyTopicRead)
def upsert_topic(
    payload: WeeklyTopicUpsert,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner_id),
) -> WeeklyTopic:
    """One topic note per (owner, term, course, week) -- editing an
    existing week just overwrites topic_text rather than accumulating
    duplicate rows."""
    if db.get(Course, payload.course_id) is None:
        raise HTTPException(status_code=404, detail=f"Course {payload.course_id} not found")

    stmt = pg_insert(WeeklyTopic).values(owner_id=owner_id, **payload.model_dump())
    stmt = stmt.on_conflict_do_update(
        index_elements=["owner_id", "term_code", "course_id", "week_start_date"],
        set_={"topic_text": stmt.excluded.topic_text},
    ).returning(WeeklyTopic)
    topic = db.execute(stmt).scalar_one()
    db.commit()
    db.refresh(topic)
    return topic


@router.delete("/topics/{topic_id}", status_code=204, response_model=None)
def delete_topic(
    topic_id: int,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner_id),
) -> None:
    topic = db.execute(
        select(WeeklyTopic).where(WeeklyTopic.id == topic_id, WeeklyTopic.owner_id == owner_id)
    ).scalar_one_or_none()
    if topic is None:
        raise HTTPException(status_code=404, detail=f"Topic {topic_id} not found")
    db.delete(topic)
    db.commit()
