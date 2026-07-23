"""
Pure functions that turn one raw Aurora `/searchResults` record into the
normalized shapes the upsert layer expects. Nothing here touches the
database or the network, which is what makes it directly unit-testable
against the sample payloads in the spec.

Aurora returns one JSON object per CRN, with that section's bundled
meeting blocks embedded in its own `meetingsFaculty` array -- so mapping is
one raw record -> one SectionData (never a group of records). That's what
keeps a CLAS + TUT pair native to a single CRN instead of getting split.
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field
from datetime import time
from typing import Any

_TERM_SUFFIX_NAMES = {
    "10": "Winter",
    "30": "Spring",
    "50": "Spring/Summer",
    "60": "Summer",
    "70": "Fall/Winter",
    "90": "Fall",
}


@dataclass(frozen=True)
class MeetingTimeData:
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


@dataclass(frozen=True)
class SectionData:
    crn: str
    term_code: str
    subject: str
    course_number: str
    course_title: str | None
    credit_hours: float | None
    section_number: str
    link_identifier: str | None
    is_linked: bool
    seats_available: int
    max_enrollment: int | None
    enrollment: int | None
    instructor: str | None
    meeting_times: list[MeetingTimeData] = field(default_factory=list)


def decode_term_description(term_code: str) -> str:
    """
    Best-effort human label from Banner's YYYY+suffix term code convention
    (e.g. "202690" -> "Fall 2026"). This is a display-only heuristic based
    on the common Banner suffix set -- an unrecognized suffix falls back to
    a generic label rather than raising, since nothing structural depends
    on getting the English name exactly right.
    """
    if len(term_code) < 6:
        return term_code
    year, suffix = term_code[:4], term_code[4:]
    label = _TERM_SUFFIX_NAMES.get(suffix, f"Term {suffix}")
    return f"{label} {year}"


def _parse_clock_time(raw: str | None) -> time | None:
    """
    Aurora sends military time as a 4-digit string ("1030"). Blank or
    missing means an async/online/TBA meeting with no clock time at all.
    """
    if not raw:
        return None
    raw = raw.strip()
    if len(raw) != 4 or not raw.isdigit():
        return None
    hour, minute = int(raw[:2]), int(raw[2:])
    return time(hour=hour, minute=minute)


def _extract_instructor(faculty: list[dict[str, Any]] | None) -> str | None:
    if not faculty:
        return None
    names = [f["displayName"] for f in faculty if f.get("displayName")]
    return html.unescape("; ".join(names)) if names else None


def _decode_html_entities(text: str | None) -> str | None:
    """
    Aurora returns free-text fields (course titles, especially French ones)
    HTML-entity-escaped, e.g. "Comptabilit&eacute; fiscale" instead of
    "Comptabilité fiscale" -- likely a side effect of Banner rendering
    these fields through an HTML template somewhere in its own pipeline
    before they reach this JSON endpoint. Left undecoded, `&eacute;`-style
    entities show up verbatim in the UI. `html.unescape` is stdlib and
    handles the full standard entity set, not just accented Latin
    characters.
    """
    if text is None:
        return None
    return html.unescape(text)


def map_meeting_time(raw_meeting: dict[str, Any]) -> MeetingTimeData | None:
    """Map one `meetingsFaculty[i]` entry. Returns None for malformed/empty entries."""
    mt = raw_meeting.get("meetingTime")
    if not mt:
        return None
    return MeetingTimeData(
        meeting_type=mt.get("meetingType") or "UNK",
        start_time=_parse_clock_time(mt.get("beginTime")),
        end_time=_parse_clock_time(mt.get("endTime")),
        monday=bool(mt.get("monday")),
        tuesday=bool(mt.get("tuesday")),
        wednesday=bool(mt.get("wednesday")),
        thursday=bool(mt.get("thursday")),
        friday=bool(mt.get("friday")),
        saturday=bool(mt.get("saturday")),
        sunday=bool(mt.get("sunday")),
    )


def map_section(raw: dict[str, Any]) -> SectionData:
    """Map one raw Aurora record (one CRN) into a normalized SectionData."""
    meeting_times = [
        parsed
        for raw_meeting in (raw.get("meetingsFaculty") or [])
        if (parsed := map_meeting_time(raw_meeting)) is not None
    ]

    #OLD code for credit hours
    #credit_hours = raw.get("creditHours")
    #if credit_hours is None:
    #    credit_hours = raw.get("creditHourLow")
    # Extract the highest available credit hour value across lecture/lab variations

    #NEW code for credit hours
    credit_hours = max(
        float(raw.get("creditHourHigh") or 0.0),
        float(raw.get("creditHours") or 0.0),
        float(raw.get("creditHourLow") or 0.0)
    )

    return SectionData(
        crn=str(raw["courseReferenceNumber"]),
        term_code=str(raw["term"]),
        subject=raw["subject"],
        course_number=str(raw["courseNumber"]),
        course_title=_decode_html_entities(raw.get("courseTitle") or None),
        credit_hours=credit_hours,
        section_number=raw["sequenceNumber"],
        link_identifier=raw.get("linkIdentifier") or None,
        is_linked=bool(raw.get("isSectionLinked")),
        seats_available=raw.get("seatsAvailable") or 0,
        max_enrollment=raw.get("maximumEnrollment"),
        enrollment=raw.get("enrollment"),
        instructor=_extract_instructor(raw.get("faculty")),
        meeting_times=meeting_times,
    )
