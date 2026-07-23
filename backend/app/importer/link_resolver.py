"""
Link resolution: turns Aurora's raw, opaque `linkIdentifier` + meeting-type
data into the normalized LinkGroup / link_group_id / link_slot relationship
the scheduler consumes.

This is the ONLY place in the codebase that interprets Aurora's linking
convention. The scheduler must never parse or slice `linkIdentifier` --
see app.models.section.Section and app.services.scheduler for why.

Resolution strategy (revised -- see note below):
1. Every `linkIdentifier` observed so far follows a letter-prefix +
   trailing-number shape: e.g. "A1" for a lecture/tutorial component,
   "B1" for a lab component. The letter varies by component type; the
   NUMBER is the actual shared pairing key Banner uses to say "these
   belong together." Confirmed directly from real data: MECH 2222's A01
   (identifier "A1") must be taken with one of B01/B02 (identifier "B1"),
   and MATH 1700's four lecture sections (all "A1") pair with all
   thirteen tutorial sections (all "B1") -- i.e. the whole course is one
   pairing family, keyed on "1". A course with two independent
   lecture/lab pairings would be expected to show "A1"/"B1" for one pair
   and "A2"/"B2" for the other; we haven't observed that case yet, but
   the number-based grouping generalizes correctly to it, while the
   previous whole-string grouping never could.
2. Group a course's is_linked=True sections by that trailing number
   (stripped of the letter prefix) -- this becomes one link_groups row
   per number, spanning every letter that shares it.
3. Within a group, assign each section a `link_slot` derived from the set
   of meeting types on its own meetings (e.g. a lecture bundling CLAS+TUT
   gets a different slot than a lab-only section). Sections sharing a
   slot are interchangeable alternatives; sections in the same group with
   different slots are separate required components. This part is
   unchanged from the original design and still looks correct.

REVISION NOTE: the original version of this module grouped by exact
equality of the raw `link_identifier` string, on the theory that section
*labels* (A01 vs B02 vs B03) don't reliably encode which sections belong
together, so nothing about the identifier should be parsed. That reasoning
is still correct for `section_number` -- it's just that it was mistakenly
applied to `link_identifier` too, which is a different field with an
actually-reliable letter+number structure, confirmed above. The result was
every linked course in the dataset splitting into disconnected components
(lecture-only bundles and lab-only bundles that could never appear
together in a schedule) instead of one combined bundle -- silently wrong
for every linked course, not just a one-off edge case.

If a `link_identifier` doesn't match the expected letter+number shape, we
fall back to grouping by the raw string (the old behavior) and log a
warning -- better to produce an overly-split-but-safe result on
unexpected data than to guess at a pairing that might be wrong.

This heuristic is not bulletproof -- it can't distinguish two genuinely
separate components that happen to share both a pairing number AND a
meeting-type makeup. It's the most defensible signal available from
Aurora's public search fields, though, and because it's fully contained
here, it can be swapped out later without the scheduler ever needing to
change.

NOTE: `crn` alone is only unique within a single term -- Banner reuses the
same CRN number for the same recurring section year over year (see
app.models.section). Every UPDATE against `sections` in this module must
therefore be scoped by (crn, term_code) together, never crn alone, or
resolving link groups for one term will silently overwrite the already-
correct link_group_id/link_slot of every other term that happens to share
that CRN number.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.importer.mapper import SectionData

logger = logging.getLogger(__name__)

# Matches an optional leading letter run followed by a trailing number,
# e.g. "A1" -> group "1", "B12" -> group "12". This is deliberately
# permissive about the letter part (any number of letters, including
# none) since we only have two confirmed examples to go on; the number
# suffix is the part doing all the actual work.
_LINK_ID_PATTERN = re.compile(r"^[A-Za-z]*(\d+)$")


def _link_family(link_identifier: str) -> str:
    """
    The shared pairing key for a link_identifier: its trailing number,
    with any letter prefix stripped. Falls back to the raw identifier
    unchanged (with a warning) if it doesn't match the expected shape --
    see module docstring's REVISION NOTE for why that's the safer default
    than guessing.
    """
    match = _LINK_ID_PATTERN.match(link_identifier)
    if match is None:
        logger.warning(
            "link_identifier %r doesn't match the expected letter+number shape; "
            "grouping by the raw string as a fallback, which may fail to pair "
            "this section with its required companion section(s)",
            link_identifier,
        )
        return link_identifier
    return match.group(1)


def _meeting_signature(section: SectionData) -> str:
    """A structural (not label-based) signature: the distinct meeting types on this section."""
    types = sorted({mt.meeting_type for mt in section.meeting_times})
    return ",".join(types) if types else "NONE"


_UPSERT_LINK_GROUP_SQL = text(
    """
    INSERT INTO link_groups (course_id, term_code, external_code)
    VALUES (:course_id, :term_code, :external_code)
    ON CONFLICT (course_id, term_code, external_code) DO UPDATE
    SET external_code = excluded.external_code
    RETURNING id
    """
)

_SET_SECTION_LINK_SQL = text(
    """
    UPDATE sections
    SET link_group_id = :link_group_id, link_slot = :link_slot
    WHERE crn = :crn AND term_code = :term_code
    """
)


def resolve_link_groups(
    session: Session,
    course_id: int,
    term_code: str,
    sections: list[SectionData],
) -> None:
    """
    Resolve and persist link_group_id/link_slot for every section of one
    course in one term. Must be called after upsert_section has already
    written all of `sections` for this course+term (this only updates
    existing rows, it doesn't insert sections).
    """
    linked = [s for s in sections if s.is_linked and s.link_identifier]

    malformed = [s for s in sections if s.is_linked and not s.link_identifier]
    for s in malformed:
        logger.warning(
            "CRN %s has is_linked=True but no link_identifier; leaving standalone (no link group)",
            s.crn,
        )

    unlinked = [s for s in sections if not s.is_linked]

    # Standalone sections (never linked, or malformed) get explicitly
    # cleared -- important on re-import, in case a section was linked in a
    # previous run and Aurora has since delisted it from that group.
    for s in unlinked + malformed:
        session.execute(
            _SET_SECTION_LINK_SQL,
            {"crn": s.crn, "term_code": term_code, "link_group_id": None, "link_slot": None},
        )

    # Group by the pairing NUMBER, not the raw identifier -- see module
    # docstring. "A1" and "B1" both belong to family "1" and must land in
    # the same group; the old exact-string grouping kept them permanently
    # split apart.
    groups: dict[str, list[SectionData]] = defaultdict(list)
    for s in linked:
        family = _link_family(s.link_identifier)  # type: ignore[arg-type]
        groups[family].append(s)

    for external_code, members in groups.items():
        link_group_id = session.execute(
            _UPSERT_LINK_GROUP_SQL,
            {"course_id": course_id, "term_code": term_code, "external_code": external_code},
        ).scalar_one()

        for member in members:
            session.execute(
                _SET_SECTION_LINK_SQL,
                {
                    "crn": member.crn,
                    "term_code": term_code,
                    "link_group_id": link_group_id,
                    "link_slot": _meeting_signature(member),
                },
            )
