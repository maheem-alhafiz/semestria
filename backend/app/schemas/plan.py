"""
Schemas for Plans -- the saveable "what if I took these courses" sandbox.
Mirrors app.models.plan / app.models.plan_item exactly; see those modules'
docstrings for the reasoning behind the shape (why PlanItem is keyed per
term, why PlanItemSection doesn't enforce one-CRN-per-slot at the DB
level, why finalizing upserts into AcademicRecord instead of overwriting).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PlanItemSectionCreate(BaseModel):
    term_code: str
    crn: str
    # Snapshot of the section's link_slot at pick time, for display only
    # -- see app.models.plan_item's docstring. Not validated against the
    # live sections table here; if it's stale, that's a display nit, not
    # a correctness problem (the CRN itself is what's authoritative).
    link_slot: str | None = None


class PlanItemSectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    term_code: str
    crn: str
    link_slot: str | None


class PlanItemCreate(BaseModel):
    term_code: str
    course_id: int
    # NOTE: nothing here enforces one CRN per link_slot -- see
    # app.models.plan_item's docstring. It's this endpoint's job (not the
    # DB's) to reject a payload that picks two different CRNs for the
    # same slot; see PUT /plans/{id}/items for where that's checked.
    chosen_sections: list[PlanItemSectionCreate] = Field(default_factory=list)


class PlanItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    term_code: str
    course_id: int
    chosen_sections: list[PlanItemSectionRead]


class PlanCreate(BaseModel):
    name: str
    top_term_code: str | None = None
    bottom_term_code: str | None = None


class PlanUpdate(BaseModel):
    """All fields optional -- only what's provided gets changed."""

    name: str | None = None
    top_term_code: str | None = None
    bottom_term_code: str | None = None


class PlanItemsReplace(BaseModel):
    """
    Body for PUT /plans/{id}/items -- a full replace of this plan's
    course selections, matching how the Planner tab actually works: the
    frontend holds the complete current selection state in memory and
    saves it wholesale, rather than sending incremental add/remove deltas.
    """

    items: list[PlanItemCreate]


class PlanSummary(BaseModel):
    """Lightweight -- no nested items. Used for the Plans list page."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    is_final: bool
    top_term_code: str | None
    bottom_term_code: str | None
    updated_at: datetime


class PlanRead(BaseModel):
    """Full detail, including every item and its chosen sections -- used
    when opening/loading a single plan into the Planner tab."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    is_final: bool
    top_term_code: str | None
    bottom_term_code: str | None
    share_token: str | None
    created_at: datetime
    updated_at: datetime
    items: list[PlanItemRead]


class PlanFinalizeResponse(BaseModel):
    plan_id: int
    upserted_count: int
    # Courses this plan previously finalized that are no longer in its
    # current selection, and were therefore removed from the transcript
    # -- see /plans/{id}/finalize's docstring for why this reconciliation
    # is necessary (dropping a course and re-finalizing must actually
    # remove it, not just leave the old row orphaned).
    removed_count: int


class PlanShareResponse(BaseModel):
    share_token: str
    # Full path fragment the frontend can build a share URL from --
    # kept as just the token (not a full URL) since the frontend knows
    # its own domain; avoids baking a hostname into API responses.
