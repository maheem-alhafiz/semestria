"""
Schedule generation engine.

Given a term and a list of desired course_ids, this produces every possible
conflict-free schedule: a schedule is one CRN-bundle per course such that no
two meeting times anywhere in the schedule overlap, and every linked
section's required partner is present.

An optional `locked_crns` set narrows this further: for any course that
has one or more of its own sections' CRNs present in `locked_crns`, only
bundles containing ALL of that course's locked CRNs are considered valid
choices for it. This is what lets the frontend's per-slot picker (pick one
lecture, pick one lab) actually constrain generation instead of always
enumerating every combination regardless of what the student chose -- see
frontend/src/store/plannerStore.ts's `sectionChoices` and
CourseGroupPicker.tsx for where these CRNs come from. A flat CRN list
(rather than a per-course mapping) is sufficient because each CRN belongs
to exactly one course within a term.

IMPORTANT: this module never interprets Aurora's `linkIdentifier` string.
It only reads the already-resolved `Section.link_group_id` (an integer FK)
and `Section.link_slot` (an opaque string) and groups by equality on those
two values. All Aurora-specific interpretation of what those values mean
happens once, at import time, in app.importer.link_resolver -- see that
module's docstring for why UManitoba's linked sections can't safely be
inferred from section labels or from slicing linkIdentifier text.

The engine works in two stages:

1. Per course, build the list of valid "atomic choices" (CandidateBundle):
   - a section with link_group_id IS NULL is its own one-CRN bundle
   - sections sharing a link_group_id are combined into every valid
     combo: one section per distinct link_slot within that group (two
     sections in the same group sharing a slot are alternatives; two
     different slots must each be satisfied)
   Bundles that conflict with themselves (e.g. bad data producing an
   overlapping pair) are dropped here, since no schedule could ever use
   them. If `locked_crns` names one or more CRNs belonging to this
   course, bundles that don't contain all of them are dropped too.

2. A backtracking search picks exactly one bundle per course, checking the
   new bundle's meetings against everything already placed before
   recursing -- this is where invalid branches get pruned early, rather
   than being discovered only once a full schedule is assembled.

Courses are searched in order of fewest available bundles first (the
"most constrained variable" heuristic), since that fails dead branches as
early as possible.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import product

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import MeetingTime, Section

logger = logging.getLogger(__name__)

_DAY_ATTRS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


# --------------------------------------------------------------------------
# Time-conflict primitives
# --------------------------------------------------------------------------


def _shares_a_day(a: MeetingTime, b: MeetingTime) -> bool:
    return any(getattr(a, day) and getattr(b, day) for day in _DAY_ATTRS)


def _times_overlap(a: MeetingTime, b: MeetingTime) -> bool:
    # Async/TBA meetings (no clock time at all) can never time-conflict.
    if a.start_time is None or a.end_time is None or b.start_time is None or b.end_time is None:
        return False
    return a.start_time < b.end_time and b.start_time < a.end_time


def meetings_conflict(a: MeetingTime, b: MeetingTime) -> bool:
    """Two meetings conflict iff they share a weekday AND their clock ranges overlap."""
    return _shares_a_day(a, b) and _times_overlap(a, b)


def _has_conflict(
    new_meetings: Sequence[MeetingTime], existing_meetings: Sequence[MeetingTime]
) -> bool:
    return any(meetings_conflict(a, b) for a in new_meetings for b in existing_meetings)


def _self_conflicts(meetings: Sequence[MeetingTime]) -> bool:
    return any(
        meetings_conflict(meetings[i], meetings[j])
        for i in range(len(meetings))
        for j in range(i + 1, len(meetings))
    )


# --------------------------------------------------------------------------
# Candidate bundle construction (per-course valid atomic choices)
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class CandidateBundle:
    """One complete, internally-consistent choice for a single course: either
    one standalone section, or a linked lecture+lab (etc.) combo."""

    crns: frozenset[str]
    sections: tuple[Section, ...]
    meetings: tuple[MeetingTime, ...]


def _make_bundle(sections: list[Section]) -> CandidateBundle:
    meetings = tuple(mt for s in sections for mt in s.meeting_times)
    return CandidateBundle(
        crns=frozenset(s.crn for s in sections),
        sections=tuple(sections),
        meetings=meetings,
    )


def build_course_options(
    sections: Sequence[Section],
    locked_crns: frozenset[str] = frozenset(),
) -> list[CandidateBundle]:
    """
    Build every valid atomic choice for one course from its raw sections.

    Groups purely by equality on the already-resolved `link_group_id` /
    `link_slot` columns -- both are opaque as far as this function is
    concerned; it never inspects what they represent, only whether two
    sections share the same value. See app.importer.link_resolver for how
    they were derived.

    `locked_crns` is the FULL set of locked CRNs across every course in
    this request -- this function only cares about the ones that are
    actually among `sections` (a locked CRN belonging to a different
    course is irrelevant here and safely ignored). If any of this
    course's own CRNs are locked, only bundles containing ALL of them
    survive; a bundle missing a locked CRN can never be what the student
    asked for, so there's no point offering it to the search.

    Pure function: takes ORM Section objects (with meeting_times already
    loaded) and returns plain CandidateBundle data -- no DB or network
    access here, so this is directly unit-testable against hand-built
    Section/MeetingTime objects.
    """
    bundles: list[CandidateBundle] = []

    standalone = [s for s in sections if s.link_group_id is None]
    for s in standalone:
        bundles.append(_make_bundle([s]))

    linked = [s for s in sections if s.link_group_id is not None]

    # link_group_id -> link_slot -> [sections filling that slot]
    families: dict[int, dict[str, list[Section]]] = defaultdict(lambda: defaultdict(list))
    for s in linked:
        families[s.link_group_id][s.link_slot or "?"].append(s)  # type: ignore[index]

    for _group_id, slots in families.items():
        slot_members = list(slots.values())  # e.g. [[lecture_section], [lab1, lab2, lab3]]
        for combo in product(*slot_members):
            bundles.append(_make_bundle(list(combo)))

    # A self-conflicting bundle (e.g. bad data producing an internally
    # overlapping pair) can never appear in any valid schedule -- drop it
    # here so the search never has to rediscover that later.
    valid_bundles = [b for b in bundles if not _self_conflicts(b.meetings)]
    dropped = len(bundles) - len(valid_bundles)
    if dropped:
        logger.warning("Dropped %d self-conflicting candidate bundle(s)", dropped)

    # Restrict to this course's own locked CRNs only -- a lock belonging
    # to some other course in the same request is not this function's
    # concern and must not filter these bundles.
    course_locked = locked_crns & {s.crn for s in sections}
    if course_locked:
        valid_bundles = [b for b in valid_bundles if course_locked <= b.crns]

    return valid_bundles


# --------------------------------------------------------------------------
# Backtracking search
# --------------------------------------------------------------------------


def _search(
    course_order: list[int],
    options_by_course: dict[int, list[CandidateBundle]],
    max_results: int | None,
) -> list[list[CandidateBundle]]:
    results: list[list[CandidateBundle]] = []
    chosen: list[CandidateBundle] = []
    busy: list[MeetingTime] = []

    def backtrack(idx: int) -> bool:
        """Returns True once max_results is reached, to unwind the recursion early."""
        if max_results is not None and len(results) >= max_results:
            return True

        if idx == len(course_order):
            results.append(list(chosen))
            return max_results is not None and len(results) >= max_results

        course_id = course_order[idx]
        for bundle in options_by_course[course_id]:
            if _has_conflict(bundle.meetings, busy):
                continue  # prune: this branch can never lead to a valid schedule

            chosen.append(bundle)
            busy_mark = len(busy)
            busy.extend(bundle.meetings)

            should_stop = backtrack(idx + 1)

            del busy[busy_mark:]
            chosen.pop()

            if should_stop:
                return True
        return False

    backtrack(0)
    return results


# --------------------------------------------------------------------------
# Public entrypoint
# --------------------------------------------------------------------------


@dataclass
class Schedule:
    """One complete, valid schedule: every selected Section for every requested course."""

    sections: list[Section]

    @property
    def crns(self) -> list[str]:
        return [s.crn for s in self.sections]


def generate_schedules(
    session: Session,
    term_code: str,
    course_ids: list[int],
    max_results: int | None = None,
    locked_crns: Sequence[str] = (),
) -> list[Schedule]:
    """
    Generate every valid, conflict-free schedule for `course_ids` in `term_code`.

    Returns an empty list if any requested course has no sections in this
    term, or has sections but no viable (non-self-conflicting, and if
    applicable not excluded by `locked_crns`) bundle -- a classic CSP
    "domain wipeout": if one variable has zero possible values, no
    complete assignment can exist, so there's no point searching further.

    `max_results` caps how many schedules are generated -- useful since a
    student picking several completely independent courses with many
    sections each can otherwise produce a very large (though finite)
    number of valid combinations.

    `locked_crns` narrows generation to only the combinations consistent
    with sections the student has explicitly chosen (e.g. via a per-slot
    picker in the UI) -- see build_course_options for how a course's
    candidate bundles get filtered by these.
    """
    if not course_ids:
        return []

    sections = (
        session.execute(
            select(Section)
            .where(Section.term_code == term_code, Section.course_id.in_(course_ids))
            .options(selectinload(Section.meeting_times), joinedload(Section.course))
        )
        .unique()
        .scalars()
        .all()
    )

    sections_by_course: dict[int, list[Section]] = defaultdict(list)
    for s in sections:
        sections_by_course[s.course_id].append(s)

    locked_crn_set = frozenset(locked_crns)

    options_by_course: dict[int, list[CandidateBundle]] = {}
    for course_id in course_ids:
        course_sections = sections_by_course.get(course_id, [])
        if not course_sections:
            logger.warning(
                "No sections found for course_id=%s in term %s -- no schedule can include it",
                course_id,
                term_code,
            )
            return []

        options = build_course_options(course_sections, locked_crns=locked_crn_set)
        if not options:
            logger.warning(
                "course_id=%s has sections but no viable bundle (after applying any locked "
                "CRNs) -- no schedule can include it",
                course_id,
            )
            return []

        options_by_course[course_id] = options

    # Most-constrained-variable first: place the course with the fewest
    # options earliest, so dead branches get pruned as early as possible.
    ordered_course_ids = sorted(course_ids, key=lambda cid: len(options_by_course[cid]))

    raw_results = _search(ordered_course_ids, options_by_course, max_results)

    return [
        Schedule(sections=[s for bundle in bundles for s in bundle.sections])
        for bundles in raw_results
    ]
