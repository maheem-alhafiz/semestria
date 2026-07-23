"""
Schemas for the grouped-sections view of a course.

A course's sections for one term are organized as:

    groups: [
      { link_group_id: 642 or None, slots: [
          { link_slot: "CLAS,TUT", options: [<one A01 section>] },
          { link_slot: "LAB",      options: [<B01>, <B02>, <B03>] },
      ]},
      ... (one more group per distinct link_group_id, plus one synthetic
           group per standalone/unlinked section)
    ]

This mirrors app.models.section.Section's link_group_id/link_slot columns
(populated by app.importer.link_resolver) directly -- see that module's
docstring for what these values mean and how they're derived from Aurora's
raw linkIdentifier field. A slot with more than one option means those
sections are interchangeable alternatives (e.g. pick one of three labs);
a group with more than one slot means those slots are separate required
components that must each be satisfied (e.g. a lecture AND a lab).

link_group_id is None for standalone sections (never linked, or Aurora's
linked data was malformed -- see link_resolver's `malformed` handling).
Each standalone section becomes its own single-slot, single-option group
so the frontend can render it identically to a real group, just with
nothing to choose between.
"""

from __future__ import annotations

from datetime import time

from pydantic import BaseModel, ConfigDict


class MeetingTimeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    meeting_type: str
    start_time: time | None
    end_time: time | None
    monday: bool
    tuesday: bool
    wednesday: bool
    thursday: bool
    friday: bool
    saturday: bool
    sunday: bool


class SectionOptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    crn: str
    section_number: str
    seats_available: int
    max_enrollment: int | None
    enrollment: int | None
    instructor: str | None
    meeting_times: list[MeetingTimeRead]


class SectionSlotRead(BaseModel):
    link_slot: str
    options: list[SectionOptionRead]


class SectionGroupRead(BaseModel):
    link_group_id: int | None
    slots: list[SectionSlotRead]


class CourseSectionsRead(BaseModel):
    course_id: int
    subject: str
    course_number: str
    title: str
    credit_hours: float
    groups: list[SectionGroupRead]
