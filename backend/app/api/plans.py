from __future__ import annotations

import secrets
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.visitor import get_current_owner_id
from app.models import AcademicRecord, Course, Plan, PlanItem, PlanItemSection
from app.schemas.plan import (
    PlanCreate,
    PlanFinalizeResponse,
    PlanItemsReplace,
    PlanRead,
    PlanShareResponse,
    PlanSummary,
    PlanUpdate,
)

router = APIRouter(prefix="/plans", tags=["plans"])

# Eager-loads a Plan's full item/section tree in one query -- every
# GET/PUT/POST below that returns a PlanRead needs this, otherwise
# Pydantic's from_attributes hits lazy-loaded relationships and either
# N+1 queries or a DetachedInstanceError once the session closes.
_PLAN_DETAIL_OPTIONS = (selectinload(Plan.items).selectinload(PlanItem.chosen_sections),)


def _get_owned_plan_or_404(db: Session, plan_id: int, owner_id: str) -> Plan:
    """
    Fetches a plan scoped to the requesting visitor. Deliberately raises
    the same 404 whether the plan doesn't exist at all OR exists but
    belongs to someone else -- never reveal via status code that a given
    plan_id belongs to another visitor.
    """
    plan = db.execute(
        select(Plan)
        .where(Plan.id == plan_id, Plan.owner_id == owner_id)
        .options(*_PLAN_DETAIL_OPTIONS)
    ).scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")
    return plan


@router.post("", response_model=PlanRead, status_code=201)
def create_plan(
    payload: PlanCreate,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner_id),
) -> Plan:
    plan = Plan(
        name=payload.name,
        owner_id=owner_id,
        top_term_code=payload.top_term_code,
        bottom_term_code=payload.bottom_term_code,
    )
    db.add(plan)
    db.commit()
    return _get_owned_plan_or_404(db, plan.id, owner_id)


@router.get("", response_model=list[PlanSummary])
def list_plans(
    db: Session = Depends(get_db), owner_id: str = Depends(get_current_owner_id)
) -> list[Plan]:
    stmt = select(Plan).where(Plan.owner_id == owner_id).order_by(Plan.updated_at.desc())
    return db.execute(stmt).scalars().all()


@router.get("/{plan_id}", response_model=PlanRead)
def get_plan(
    plan_id: int, db: Session = Depends(get_db), owner_id: str = Depends(get_current_owner_id)
) -> Plan:
    return _get_owned_plan_or_404(db, plan_id, owner_id)


@router.patch("/{plan_id}", response_model=PlanRead)
def update_plan(
    plan_id: int,
    payload: PlanUpdate,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner_id),
) -> Plan:
    plan = _get_owned_plan_or_404(db, plan_id, owner_id)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(plan, field, value)
    db.commit()
    return _get_owned_plan_or_404(db, plan_id, owner_id)


@router.delete("/{plan_id}", status_code=204, response_model=None)
def delete_plan(
    plan_id: int, db: Session = Depends(get_db), owner_id: str = Depends(get_current_owner_id)
) -> None:
    plan = db.execute(
        select(Plan).where(Plan.id == plan_id, Plan.owner_id == owner_id)
    ).scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")
    # PlanItem/PlanItemSection cascade via ondelete="CASCADE" on their FKs
    # to plans.id -- deleting the Plan row is enough. AcademicRecord rows
    # this Plan previously finalized are NOT touched: source_plan_id is
    # ondelete="SET NULL", not CASCADE, by design (see
    # app.models.academic_record's docstring) -- a permanent record must
    # survive its originating Plan being deleted.
    db.delete(plan)
    db.commit()


@router.put("/{plan_id}/items", response_model=PlanRead)
def replace_plan_items(
    plan_id: int,
    payload: PlanItemsReplace,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner_id),
) -> Plan:
    """
    Wholesale-replaces every course selection in this plan with exactly
    what's in `payload.items` -- matching how the Planner tab's frontend
    state actually works (see PlanItemsReplace's docstring). Any course
    previously in the plan but missing from this payload is removed.

    Validates that no course_id has two different CRNs claiming the same
    link_slot within one term -- the DB schema deliberately doesn't
    enforce this (see app.models.plan_item's docstring), so it's checked
    here instead.
    """
    # Ownership check first -- confirms this plan_id belongs to this
    # visitor before touching any items.
    owned_plan = db.execute(
        select(Plan.id).where(Plan.id == plan_id, Plan.owner_id == owner_id)
    ).scalar_one_or_none()
    if owned_plan is None:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")

    for item in payload.items:
        slot_to_crns: dict[str, set[str]] = defaultdict(set)
        for section in item.chosen_sections:
            if section.link_slot is not None:
                slot_to_crns[section.link_slot].add(section.crn)
        conflicting = {slot: crns for slot, crns in slot_to_crns.items() if len(crns) > 1}
        if conflicting:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"course_id={item.course_id} term={item.term_code}: more than one CRN "
                    f"chosen for the same slot ({conflicting}) -- a slot can only have one "
                    "chosen section at a time."
                ),
            )

    # Deleting existing PlanItems cascades to their PlanItemSections
    # automatically (ondelete="CASCADE") -- simplest correct way to do a
    # full replace without hand-diffing old vs new selections.
    db.execute(delete(PlanItem).where(PlanItem.plan_id == plan_id))
    db.flush()

    for item in payload.items:
        plan_item = PlanItem(plan_id=plan_id, term_code=item.term_code, course_id=item.course_id)
        db.add(plan_item)
        db.flush()  # populate plan_item.id for the child rows below
        for section in item.chosen_sections:
            db.add(
                PlanItemSection(
                    plan_item_id=plan_item.id,
                    term_code=section.term_code,
                    crn=section.crn,
                    link_slot=section.link_slot,
                )
            )

    db.commit()
    return _get_owned_plan_or_404(db, plan_id, owner_id)


@router.post("/{plan_id}/finalize", response_model=PlanFinalizeResponse)
def finalize_plan(
    plan_id: int, db: Session = Depends(get_db), owner_id: str = Depends(get_current_owner_id)
) -> dict:
    """
    Upserts every course currently in this plan into AcademicRecord --
    keyed by (owner_id, term_code, course_id) -- and reconciles away
    anything this SAME plan previously pushed that's no longer in its
    current selection. This is what makes re-finalizing after editing a
    plan behave correctly: e.g. drop a course from an already-finalized
    term, hit Finalize again, and the dropped course's transcript row is
    removed too, not left orphaned.

    `is_final` is not a mutually-exclusive "the one true plan" flag --
    it's per-plan, meaning "has been pushed to the transcript." Multiple
    plans can be_final=True simultaneously as long as they're not making
    contradictory claims about the same term; the DB-level truth for any
    given (owner_id, term_code, course_id) is always whichever finalize
    ran most recently. Reconciliation only ever touches rows THIS plan
    owns (source_plan_id == plan.id) -- a different plan's rows, or a
    manually added past course (source_plan_id NULL), are never touched
    here.

    `grade` is intentionally left alone on upsert conflict (only set on
    first insert, where it starts NULL/"in progress") -- re-finalizing an
    already-graded term must never wipe out a grade entered via the
    Degree Tracker's own edit control.

    An empty plan (every course removed, then finalized) is allowed --
    it's a legitimate way to retract everything this plan previously
    pushed, via the same reconciliation path.
    """
    plan = _get_owned_plan_or_404(db, plan_id, owner_id)

    current_keys = {(item.term_code, item.course_id) for item in plan.items}

    previously_owned = db.execute(
        select(AcademicRecord).where(
            AcademicRecord.source_plan_id == plan.id, AcademicRecord.owner_id == owner_id
        )
    ).scalars().all()

    removed = 0
    for record in previously_owned:
        if (record.term_code, record.course_id) not in current_keys:
            db.delete(record)
            removed += 1

    course_ids = {item.course_id for item in plan.items}
    courses_by_id = (
        {
            c.course_id: c
            for c in db.execute(
                select(Course).where(Course.course_id.in_(course_ids))
            ).scalars()
        }
        if course_ids
        else {}
    )

    upserted = 0
    for item in plan.items:
        course = courses_by_id[item.course_id]
        stmt = pg_insert(AcademicRecord).values(
            owner_id=owner_id,
            term_code=item.term_code,
            course_id=item.course_id,
            source_plan_id=plan.id,
            # crn intentionally NULL for plan-sourced rows -- see
            # AcademicRecordRead's docstring note on why a single CRN
            # isn't meaningful when a course has multiple sections.
            crn=None,
            title_snapshot=course.title,
            credit_hours_snapshot=course.credit_hours,
            grade=None,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["owner_id", "term_code", "course_id"],
            set_={
                "source_plan_id": stmt.excluded.source_plan_id,
                "title_snapshot": stmt.excluded.title_snapshot,
                "credit_hours_snapshot": stmt.excluded.credit_hours_snapshot,
                # grade deliberately omitted -- see function docstring.
            },
        )
        db.execute(stmt)
        upserted += 1

    plan.is_final = True
    db.commit()

    return {"plan_id": plan_id, "upserted_count": upserted, "removed_count": removed}


@router.post("/{plan_id}/share", response_model=PlanShareResponse)
def share_plan(
    plan_id: int, db: Session = Depends(get_db), owner_id: str = Depends(get_current_owner_id)
) -> dict:
    """
    Generates (or returns the existing) share token for this plan.
    Idempotent -- calling this twice on an already-shared plan returns
    the same token rather than invalidating the old link, since a
    previously-shared URL someone already has should keep working.
    """
    plan = db.execute(
        select(Plan).where(Plan.id == plan_id, Plan.owner_id == owner_id)
    ).scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")

    if plan.share_token is None:
        # token_urlsafe(32) produces a 43-character string -- matches
        # Plan.share_token's String(43) column exactly. If this ever
        # changes, the column length needs to change with it.
        plan.share_token = secrets.token_urlsafe(32)
        db.commit()

    return {"share_token": plan.share_token}


@router.get("/shared/{token}", response_model=PlanRead)
def get_shared_plan(token: str, db: Session = Depends(get_db)) -> Plan:
    """
    Public, read-only lookup by share token -- no plan_id needed, so a
    shared URL doesn't leak or depend on the owner's internal plan IDs.

    DELIBERATE EXCEPTION: this is the one route in this file that does
    NOT filter by owner_id / does not depend on get_current_owner_id at
    all. That's intentional -- a share link is meant to work for anyone
    who has it, including someone with no prior visitor cookie at all.
    """
    plan = db.execute(
        select(Plan).where(Plan.share_token == token).options(*_PLAN_DETAIL_OPTIONS)
    ).scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail="No plan found for this share link")
    return plan
