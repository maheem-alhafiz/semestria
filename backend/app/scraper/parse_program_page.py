r"""
Program page parsing.

Two independent things live on one program page (confirmed directly from
the Mechanical Engineering B.Sc. fetch: "Degree Requirements",
"Concentrations", "Preliminary Engineering Program", and "Courses" are
all anchors on the SAME page, not separate pages):

1. Course-list TABLES (parse_course_list_tables) -- these are the raw
   material for RequirementGroup/RequirementGroupCourse rows. Each table
   becomes one candidate group with a label (from the nearest heading)
   and a list of rows. This is intentionally RAW output, not classified
   -- nothing here decides ALL vs ONE_OF vs N_OF; that's a human's call
   during the review step (see app.scraper.import_requirements' docstring
   and the conversation this schema came out of on why auto-classifying
   kind is not attempted).

2. Course description BLOCKS (parse_course_blocks) -- these are what
   populate Course.prerequisites_text/corequisites_text (raw prose,
   always) and course_relationships (Equiv To / Mutually Exclusive --
   RELIABLY structured as a label followed by a plain comma-separated
   course-code list, so these get parsed into structured pairs directly,
   not left as text).

Course-code extraction throughout uses a regex on cell/line TEXT
(r'\b([A-Z]{2,5})\s?(\d{3,4})\b') rather than depending on exact link/
class markup -- course codes have a very consistent visual shape
regardless of whether CourseLeaf wraps them in an <a> tag, a <strong>, or
plain text, so this is more robust to markup variation than selector-only
extraction. Table/block CONTAINER detection still tries CourseLeaf's
standard class names first (`sc_courselist`, `courseblock`) since those
are well-established across CourseLeaf installs, with a text-shape
fallback for finding course-list tables if the class name doesn't match
(see _find_course_list_tables).
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup, Tag

_COURSE_CODE_RE = re.compile(r"\b([A-Z]{2,6})\s?(\d{3,4})\b")
_FOOTNOTE_REF_RE = re.compile(r"\s*(\d+)\s*$")  # trailing superscript digit(s) on a cell
_REQUISITE_LABEL_START_RE = re.compile(
    r"^\s*(?:PR/CR|Prerequisites?|Corequisites?|Pre-?\s*or\s*[Cc]orequisites?|"
    r"Equiv(?:alent)?\s*To|Mutually Exclusive)\s*:",
    re.IGNORECASE,
)


@dataclass
class RawCourseListRow:
    raw_text: str
    course_code: str | None  # "MECH 2112", normalized "SUBJ NUM"
    is_alternative: bool  # True for an "or X" row -- alternative to the row above
    hours_text: str | None
    footnote_refs: list[int] = field(default_factory=list)


@dataclass
class RawRequirementGroup:
    label: str
    rows: list[RawCourseListRow]
    footnotes: dict[int, str]
    source_heading_level: str  # "h2"/"h3"/"h4" -- hints at nesting for review


@dataclass
class RawCourseBlock:
    subject: str
    course_number: str
    title: str
    credit_hours: float | None
    description: str
    prerequisites_text: str | None
    corequisites_text: str | None
    equiv_to: list[str]
    mutually_exclusive: list[str]


def _normalize_code(subject: str, number: str) -> str:
    return f"{subject.upper()} {number}"


def _clean_spacing(text: str) -> str:
    """get_text(" ", ...) inserts a space at every tag boundary regardless
    of the original adjacency, producing artifacts like 'ENG 1460 , (' or
    'MATH 1710 ) .' -- collapse those back to normal prose spacing."""
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([.,;:)])", r"\1", text)
    text = re.sub(r"([(])\s+", r"\1", text)
    return text


def _find_course_list_tables(soup: BeautifulSoup) -> list[Tag]:
    tables = soup.find_all("table", class_="sc_courselist")
    if tables:
        return tables
    # Fallback: any table whose header row looks like Course/Title/Hours.
    fallback = []
    for table in soup.find_all("table"):
        header_text = " ".join(th.get_text(strip=True) for th in table.find_all("th")).lower()
        if "course" in header_text and ("hour" in header_text or "title" in header_text):
            fallback.append(table)
    return fallback


def _nearest_preceding_heading(table: Tag) -> tuple[str, str]:
    """Walk backwards through preceding siblings/ancestors for the closest
    h2/h3/h4 -- that's this table's group label."""
    for el in table.find_all_previous(["h2", "h3", "h4"]):
        text = el.get_text(strip=True)
        if text:
            return text, el.name
    return "Unlabeled Requirement Group", "h2"


def _parse_footnotes_near(table: Tag) -> dict[int, str]:
    """CourseLeaf typically lists footnotes as a series of numbered
    paragraphs/list items immediately following the table, each starting
    with a bare number. Collected from the next few sibling elements
    after the table until something that doesn't look like a footnote."""
    footnotes: dict[int, str] = {}
    node = table
    for _ in range(30):  # bounded walk -- don't run off into the next section
        node = node.find_next_sibling()
        if node is None:
            break
        text = node.get_text(" ", strip=True)
        if not text:
            continue
        match = re.match(r"^(\d+)\s+(.*)", text)
        if match:
            footnotes[int(match.group(1))] = match.group(2)
        else:
            # Hit a non-footnote element -- assume footnotes ended.
            if footnotes:
                break
    return footnotes


def parse_course_list_tables(soup: BeautifulSoup) -> list[RawRequirementGroup]:
    groups: list[RawRequirementGroup] = []

    for table in _find_course_list_tables(soup):
        label, heading_level = _nearest_preceding_heading(table)
        footnotes = _parse_footnotes_near(table)

        rows: list[RawCourseListRow] = []
        for tr in table.find_all("tr"):
            cells = tr.find_all(["td", "th"])
            if not cells or tr.find("th"):
                continue  # header row

            row_text = " | ".join(c.get_text(" ", strip=True) for c in cells)
            first_cell_text = cells[0].get_text(" ", strip=True)

            is_alternative = first_cell_text.lower().startswith("or ") or first_cell_text.lower() == "or"

            code_match = _COURSE_CODE_RE.search(row_text)
            course_code = _normalize_code(*code_match.groups()) if code_match else None

            hours_text = cells[-1].get_text(strip=True) if len(cells) > 1 else None
            # A pure "or" row usually has an empty last cell (see module
            # docstring's example) -- don't treat empty string as real hours.
            hours_text = hours_text or None

            footnote_refs = []
            for sup in tr.find_all("sup"):
                sup_digits = re.findall(r"\d+", sup.get_text())
                footnote_refs.extend(int(n) for n in sup_digits)

            rows.append(
                RawCourseListRow(
                    raw_text=row_text,
                    course_code=course_code,
                    is_alternative=is_alternative,
                    hours_text=hours_text,
                    footnote_refs=footnote_refs,
                )
            )

        if rows:
            groups.append(
                RawRequirementGroup(
                    label=label,
                    rows=rows,
                    footnotes=footnotes,
                    source_heading_level=heading_level,
                )
            )

    return groups


def _extract_relationship_list(text: str) -> list[str]:
    """'Equiv To: MECH 2200' or 'Mutually Exclusive: CIVL 2830, ENG 2020,
    MECH 2010' -> ['MECH 2200'] / ['CIVL 2830', 'ENG 2020', 'MECH 2010'].
    Codes with no live catalog listing (the former MECH 2260-style, or a
    course removed from the current calendar) still match the same regex
    shape -- resolving whether they exist in `courses` is
    import_requirements' job, not this parser's."""
    return [_normalize_code(*m.groups()) for m in _COURSE_CODE_RE.finditer(text)]


def parse_course_blocks(soup: BeautifulSoup) -> list[RawCourseBlock]:
    blocks: list[RawCourseBlock] = []

    for block in soup.find_all("div", class_="courseblock"):
        title_el = block.find(class_="courseblocktitle") or block
        title_text = title_el.get_text(" ", strip=True)

        code_match = _COURSE_CODE_RE.search(title_text)
        if not code_match:
            continue  # not actually a course header, skip
        subject, number = code_match.groups()

        # Title is whatever's left after stripping the code and a
        # trailing "N cr" credit-hours marker.
        remainder = title_text[code_match.end():]
        credit_match = re.search(r"([\d.]+)\s*cr\b", remainder, re.IGNORECASE)
        credit_hours = float(credit_match.group(1)) if credit_match else None
        title = remainder[: credit_match.start()].strip() if credit_match else remainder.strip()
        title = title.strip(" -")

        # There's no distinct "this is the description" class on this site
        # -- description AND prerequisites/corequisites/equiv/mutually-
        # exclusive all live in SEPARATE sibling <div class="courseblockextra
        # noindent"> elements, distinguished only by CONTENT (their leading
        # label), not class name. Each div is classified and extracted
        # independently below, rather than joining the whole course block
        # into one flat string first -- an earlier version tried the
        # latter and a Prerequisite div's text bled straight into the next
        # unrelated Mutually Exclusive div, since there's no <br/> between
        # separate divs for the parser to treat as a boundary.
        _COREQ_LABEL = r"(?:Pre-?\s*or\s*[Cc]orequisites?|Corequisites?)\s*:"

        description = ""
        prerequisites_text: str | None = None
        corequisites_text: str | None = None
        equiv_to: list[str] = []
        mutually_exclusive: list[str] = []

        for extra_el in block.find_all(class_="courseblockextra"):
            # <br/> tags are the only genuine visual line break within a
            # single div (e.g. "PR/CR: ...<br/>Prerequisites: ..."). Using
            # get_text("\n", ...) directly would ALSO insert a break at
            # every inline <a> tag boundary, truncating any multi-course
            # requisite line at its first linked course code -- so replace
            # only real <br/> tags with "\n" first, then join everything
            # else with a plain space (see _clean_spacing for the
            # resulting spacing artifact cleanup).
            extra_copy = copy.copy(extra_el)
            for br in extra_copy.find_all("br"):
                br.replace_with("\n")
            text = _clean_spacing(extra_copy.get_text(" ", strip=True))
            if not text:
                continue

            if not _REQUISITE_LABEL_START_RE.match(text):
                if not description:
                    description = text
                continue

            prereq_match = re.search(
                rf"Prerequisites?:\s*(.+?)(?:\n|(?={_COREQ_LABEL})|$)", text
            )
            if prereq_match:
                prerequisites_text = prereq_match.group(1).strip()

            coreq_match = re.search(rf"{_COREQ_LABEL}\s*(.+?)(?:\n|$)", text)
            if coreq_match:
                corequisites_text = coreq_match.group(1).strip()

            equiv_match = re.search(r"Equiv(?:alent)?\s*To:\s*(.+?)(?:\n|$)", text)
            if equiv_match:
                equiv_to = _extract_relationship_list(equiv_match.group(1))

            mutex_match = re.search(r"Mutually Exclusive:\s*(.+?)(?:\n|$)", text)
            if mutex_match:
                mutually_exclusive = _extract_relationship_list(mutex_match.group(1))

        blocks.append(
            RawCourseBlock(
                subject=subject.upper(),
                course_number=number,
                title=title,
                credit_hours=credit_hours,
                description=description,
                prerequisites_text=prerequisites_text,
                corequisites_text=corequisites_text,
                equiv_to=equiv_to,
                mutually_exclusive=mutually_exclusive,
            )
        )

    return blocks
