"""
Manual Requirement Fulfillments API.

The escape hatch for elective buckets too broad/prose-only to auto-match
(Written English, Indigenous Knowledge, "any 1000-level HIST course") --
see app.models.manual_fulfillment's docstring. Two routes:

- POST   /manual-fulfillments        -- assign one of the visitor's own
                                          AcademicRecord rows to a group
- DELETE /manual-fulfillments/{id}   -- unassign it

Both are scoped to the requesting visitor's own owner_id -- a visitor can
only assign/remove fulfillments against their OWN academic_record rows,
never someone else's, even if they somehow guessed a valid id.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.visitor import get_current_owner_id
from app.models import AcademicRecord, ManualRequirementFulfillment, RequirementGroup

router = APIRouter(prefix="/manual-fulfillments", tags=["manual-fulfillments"])


class ManualFulfillmentCreate(BaseModel):
    requirement_group_id: int
    academic_record_id: int
    # Optional -- see ManualRequirementFulfillment's docstring on the
    # Written English credit-spillover case. Omit for the ordinary case
    # (the whole course's credit hours count toward this group).
    credit_hours_applied: float | None = None


class ManualFulfillmentRead(BaseModel):
    id: int
    requirement_group_id: int
    academic_record_id: int
    credit_hours_applied: float | None

    class Config:
        from_attributes = True


@router.post("", response_model=ManualFulfillmentRead, status_code=201)
def create_manual_fulfillment(
    payload: ManualFulfillmentCreate,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner_id),
) -> ManualRequirementFulfillment:
    # Both lookups are owner_id-scoped where it matters: the record MUST
    # belong to this visitor (that's the actual security boundary); the
    # group is shared reference data (no owner_id column), just needs to
    # exist.
    record = db.execute(
        select(AcademicRecord).where(
            AcademicRecord.id == payload.academic_record_id,
            AcademicRecord.owner_id == owner_id,
        )
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"Academic record {payload.academic_record_id} not found for this visitor",
        )

    group = db.get(RequirementGroup, payload.requirement_group_id)
    if group is None:
        raise HTTPException(
            status_code=404, detail=f"Requirement group {payload.requirement_group_id} not found"
        )

    existing = db.execute(
        select(ManualRequirementFulfillment).where(
            ManualRequirementFulfillment.owner_id == owner_id,
            ManualRequirementFulfillment.requirement_group_id == payload.requirement_group_id,
            ManualRequirementFulfillment.academic_record_id == payload.academic_record_id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        # Idempotent-ish: this exact assignment already exists, just
        # return it rather than erroring -- a double-click on "Assign"
        # shouldn't be a hard failure.
        return existing

    fulfillment = ManualRequirementFulfillment(
        owner_id=owner_id,
        requirement_group_id=payload.requirement_group_id,
        academic_record_id=payload.academic_record_id,
        credit_hours_applied=payload.credit_hours_applied,
    )
    db.add(fulfillment)
    db.commit()
    db.refresh(fulfillment)
    return fulfillment


@router.delete("/{fulfillment_id}", status_code=204)
def delete_manual_fulfillment(
    fulfillment_id: int,
    db: Session = Depends(get_db),
    owner_id: str = Depends(get_current_owner_id),
) -> None:
    fulfillment = db.execute(
        select(ManualRequirementFulfillment).where(
            ManualRequirementFulfillment.id == fulfillment_id,
            ManualRequirementFulfillment.owner_id == owner_id,
        )
    ).scalar_one_or_none()
    if fulfillment is None:
        raise HTTPException(status_code=404, detail=f"Manual fulfillment {fulfillment_id} not found")
    db.delete(fulfillment)
    db.commit()
