"""
Plans table.

A Plan is a sandbox: a named, saveable "what if I took these courses"
workspace spanning one or more terms (typically two, matching the
Planner tab's two stacked calendars, but nothing here hardcodes that --
`plan_items` can reference any number of distinct terms). It is
deliberately NOT the source of truth for what a student has actually
taken -- that's `AcademicRecord`. "Mark as Final" reads a Plan's items
and upserts them into AcademicRecord; it never deletes or mutates the
Plan itself, so a Plan stays inspectable/editable/re-loadable after
finalizing, and finalizing two different Plans (e.g. two different
years) never overwrites an unrelated year's record.

`owner_id` ties every Plan to one anonymous visitor (see
app.core.visitor) -- every query against this table must filter by the
requesting visitor's owner_id, or one visitor's plans would be readable/
editable by anyone. The one deliberate exception is GET
/plans/shared/{token}, which is meant to expose one specific plan to
anyone holding that link regardless of owner_id.

`top_term_code` / `bottom_term_code` capture which term was showing in
which of the Planner's two stacked calendar slots when the Plan was
saved, so "Load" can restore that exact layout instead of guessing from
whatever terms happen to appear in `plan_items`. Both are nullable --
a brand new, not-yet-configured Plan may not have either set yet.

`share_token` backs the "generate a shareable link" feature: NULL until
the user explicitly requests a share link (at which point the API layer
generates and stores a random token here), so a Plan is not accidentally
shareable by default.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.plan_item import PlanItem
    from app.models.term import Term


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Cookie-derived anonymous visitor id (see app.core.visitor). Every
    # query against this table must filter on this column, except the
    # explicit public share-link lookup -- see module docstring.
    owner_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Once true, this Plan's items have been upserted into AcademicRecord
    # at least once. Re-saving/re-finalizing an already-final Plan is
    # allowed (it just upserts again) -- this flag is for UI display
    # ("Mark as Final" vs "already finalized"), not a one-way lock, and
    # is NOT mutually exclusive across Plans -- see
    # app.api.plans.finalize_plan's docstring for why multiple Plans can
    # legitimately be_final=True at once.
    is_final: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    top_term_code: Mapped[str | None] = mapped_column(
        ForeignKey("terms.term_code", ondelete="SET NULL"), nullable=True
    )
    bottom_term_code: Mapped[str | None] = mapped_column(
        ForeignKey("terms.term_code", ondelete="SET NULL"), nullable=True
    )

    # NULL until a share link is explicitly requested. Unique so a token
    # can be looked up directly (GET /plans/shared/{token}) without also
    # needing the plan id.
    share_token: Mapped[str | None] = mapped_column(
        String(43), unique=True, nullable=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    top_term: Mapped["Term | None"] = relationship(foreign_keys=[top_term_code])
    bottom_term: Mapped["Term | None"] = relationship(foreign_keys=[bottom_term_code])
    items: Mapped[list["PlanItem"]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Plan id={self.id} {self.name!r} is_final={self.is_final}>"
