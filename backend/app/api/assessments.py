"""
API for the Assessments tab. See app.models.assessment for the full
reasoning behind each table's shape.

Every route filters by owner_id (the anonymous visitor cookie -- see
app.core.visitor), same as Plans/AcademicRecord.
"""

from __future__ import annotations

from datetime import date, timedelta
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.visitor import get_current_owner_id
from app.models import (
    AcademicRecord,
    Assessment,
    Course,
    GradeScaleCutoff,
    Todo,
    TrackedCourse,
    WeeklyTopic,
)
from app.schemas.assessment import (
    LETTER_GRADES,
    AssessmentCourseRead,
    AssessmentCreate,
    AssessmentRead,
    AssessmentUpdate,
    GradeScaleCourseRead,
    GradeScaleCutoffItem,
    GradeScaleUpdate,
    TodoCreate,
    TodoRead,
    TodoUpdate,
    TopicEntryCreate,
    TopicEntryRead,
    TopicEntryUpdate,
    TrackedCourseCreate,
)

router = APIRouter(prefix="/assessments", tags=["assessments"])


def _monday_of(d: date) -> date:
    """Snaps any date to that week's Monday -- see WeeklyTopic's
    docstring on why entries are stored by week rather than exact date."""
    return d - timedelta(days=d.weekday())


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
    Union of two sources -- see app.models.assessment's docstring:
      - "finalized": every course_id in this owner's AcademicRecord for
        this term (i.e. an actually-finalized schedule, via "Mark as
        Final" on a Plan -- NOT every course sitting in some throwaway
        what-if Plan that was never finalized).
      - "manual": every course_id explicitly added via POST /courses
        below.
    """
    finalized_course_ids = set(
        db.execute(
            select(AcademicRecord.course_id).where(
                AcademicRecord.owner_id == owner_id, AcademicRecord.term_code == term_code
            )
        ).scalars()
    )
    manual_course_ids = set(
        db.execute(
            select(TrackedCourse.course_id).where(
                TrackedCourse.owner_id == owner_id, TrackedCourse.term_code == term_code
            )
        ).scalars()
    )

    all_ids = finalized_course_ids | manual_course_ids
    if not all_ids:
        return []

    courses = db.execute(select(Course).where(Course.course_id.in_(all_ids))).scalars().all()
    return [
        AssessmentCourseRead(
            course_id=c.course_id,
            subject=c.subject,
            course_number=c.course_number,
            title=c.title,
            credit_hours=c.credit_hours,
            source="finalized" if c.course_id in finalized_course_ids else "manual",
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
    stmt = stmt.on_conflict_do_nothing(index_elements=["owner_id", "term_code", "course_id"])
    db.execute(stmt)
    db.commit()

    return AssessmentCourseRead(
        course_id=course.course_id,
        subject=course.subject,
        course_number=course.course_number,
        title=course.title,
        credit_hours=course.credit_hours,
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
    the owner's AcademicRecord for this term, it'll keep showing up (see
    list_tracked_courses) -- that's by design. Existing
    Assessment/WeeklyTopic rows for the course are left untouched either
    way.
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
    stmt = select(Assessment).where(Assessment.owner_id == owner_id, Assessment.term_code == term_code)
    if course_id is not None:
        stmt = stmt.where(Assessment.course_id == course_id)
    # Nulls last: unscheduled items (no due_date yet) sort after dated ones.
    stmt = stmt.order_by(Assessment.due_date.is_(None), Assessment.due_date, Assessment.due_time, Assessment.title)
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


# -- Topics log ---------------------------------------------------------


@router.get("/topics", response_model=list[TopicEntryRead])
def list_topics(
    term_code: str = Query(...),
    course_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner_id),
) -> list[WeeklyTopic]:
    stmt = select(WeeklyTopic).where(WeeklyTopic.owner_id == owner_id, WeeklyTopic.term_code == term_code)
    if course_id is not None:
        stmt = stmt.where(WeeklyTopic.course_id == course_id)
    stmt = stmt.order_by(WeeklyTopic.week_start_date, WeeklyTopic.created_at)
    return db.execute(stmt).scalars().all()


@router.post("/topics", response_model=TopicEntryRead, status_code=201)
def create_topic(
    payload: TopicEntryCreate,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner_id),
) -> WeeklyTopic:
    if db.get(Course, payload.course_id) is None:
        raise HTTPException(status_code=404, detail=f"Course {payload.course_id} not found")

    topic = WeeklyTopic(
        owner_id=owner_id,
        term_code=payload.term_code,
        course_id=payload.course_id,
        week_start_date=_monday_of(payload.entry_date),
        topic_text=payload.topic_text,
    )
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return topic


@router.patch("/topics/{topic_id}", response_model=TopicEntryRead)
def update_topic(
    topic_id: int,
    payload: TopicEntryUpdate,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner_id),
) -> WeeklyTopic:
    topic = db.execute(
        select(WeeklyTopic).where(WeeklyTopic.id == topic_id, WeeklyTopic.owner_id == owner_id)
    ).scalar_one_or_none()
    if topic is None:
        raise HTTPException(status_code=404, detail=f"Topic {topic_id} not found")

    if payload.topic_text is not None:
        topic.topic_text = payload.topic_text
    if payload.entry_date is not None:
        topic.week_start_date = _monday_of(payload.entry_date)

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


# -- To-dos ---------------------------------------------------------------


@router.get("/todos", response_model=list[TodoRead])
def list_todos(
    term_code: str = Query(...),
    course_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner_id),
) -> list[Todo]:
    stmt = select(Todo).where(Todo.owner_id == owner_id, Todo.term_code == term_code)
    if course_id is not None:
        stmt = stmt.where(Todo.course_id == course_id)
    stmt = stmt.order_by(Todo.is_done, Todo.due_date.is_(None), Todo.due_date, Todo.created_at)
    return db.execute(stmt).scalars().all()


@router.post("/todos", response_model=TodoRead, status_code=201)
def create_todo(
    payload: TodoCreate,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner_id),
) -> Todo:
    if payload.course_id is not None and db.get(Course, payload.course_id) is None:
        raise HTTPException(status_code=404, detail=f"Course {payload.course_id} not found")

    todo = Todo(owner_id=owner_id, **payload.model_dump())
    db.add(todo)
    db.commit()
    db.refresh(todo)
    return todo


@router.patch("/todos/{todo_id}", response_model=TodoRead)
def update_todo(
    todo_id: int,
    payload: TodoUpdate,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner_id),
) -> Todo:
    todo = db.execute(select(Todo).where(Todo.id == todo_id, Todo.owner_id == owner_id)).scalar_one_or_none()
    if todo is None:
        raise HTTPException(status_code=404, detail=f"Todo {todo_id} not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(todo, field, value)
    db.commit()
    db.refresh(todo)
    return todo


@router.delete("/todos/{todo_id}", status_code=204, response_model=None)
def delete_todo(
    todo_id: int,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner_id),
) -> None:
    todo = db.execute(select(Todo).where(Todo.id == todo_id, Todo.owner_id == owner_id)).scalar_one_or_none()
    if todo is None:
        raise HTTPException(status_code=404, detail=f"Todo {todo_id} not found")
    db.delete(todo)
    db.commit()


# -- Grade scale (personal percent-to-letter cutoffs per course) -------

_SUGGESTED_DEFAULT_CUTOFFS: dict[str, float] = {
    "A+": 90.0,
    "A": 80.0,
    "B+": 75.0,
    "B": 70.0,
    "C+": 65.0,
    "C": 60.0,
    "D": 50.0,
    "Fail": 0.0,
}

@router.get("/grade-scales", response_model=list[GradeScaleCourseRead])
def get_all_grade_scales(
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner_id),
) -> list[GradeScaleCourseRead]:
    """Returns all custom grade scales the student has set, grouped by course."""
    rows = db.execute(
        select(GradeScaleCutoff).where(GradeScaleCutoff.owner_id == owner_id)
    ).scalars().all()
    
    grouped = defaultdict(list)
    for r in rows:
        grouped[r.course_id].append(GradeScaleCutoffItem(letter_grade=r.letter_grade, min_percent=r.min_percent))
        
    return [
        GradeScaleCourseRead(course_id=cid, cutoffs=cutoffs)
        for cid, cutoffs in grouped.items()
    ]

@router.put("/grade-scales/{course_id}", response_model=GradeScaleCourseRead)
def set_grade_scale(
    course_id: int,
    payload: GradeScaleUpdate,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner_id),
) -> GradeScaleCourseRead:
    """Full replace of the grade scale for a specific course."""
    provided = {c.letter_grade for c in payload.cutoffs}
    missing = set(LETTER_GRADES) - provided
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing cutoffs for: {sorted(missing)}")

    db.execute(delete(GradeScaleCutoff).where(
        GradeScaleCutoff.owner_id == owner_id, 
        GradeScaleCutoff.course_id == course_id
    ))
    
    for cutoff in payload.cutoffs:
        db.add(
            GradeScaleCutoff(
                owner_id=owner_id,
                course_id=course_id,
                letter_grade=cutoff.letter_grade,
                min_percent=cutoff.min_percent
            )
        )
    db.commit()
    return GradeScaleCourseRead(course_id=course_id, cutoffs=payload.cutoffs)