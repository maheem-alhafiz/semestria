"""
Aurora (Ellucian Banner 9 Self-Service Registration) HTTP client.

Banner's public class search API is stateful: a session must first visit
the search page and "select" a term before `/searchResults` will return
data for that term. This client reproduces that handshake, then -- since
a blank-search query silently truncates at Aurora's internal record limit
-- enumerates every subject for the term via `/classSearch/get_subject`
and paginates through `/searchResults` once per subject using
`txt_subject` + pageOffset/pageMaxSize until each subject's own
totalCount is reached. Banner also appears to cache search criteria
server-side per session rather than re-reading them fresh from every
request, so `/classSearch/resetDataForm` is called before each new
subject's search to clear that stored state -- see `_reset_search_form`
for the evidence behind this.

IMPORTANT: The endpoint paths and handshake below follow the standard
Ellucian Banner 9 SSB convention used by many universities' registration
systems, including UManitoba's Aurora. This code has *not* been exercised
against the live aurora-registration.umanitoba.ca host -- this sandbox's
outbound network access is restricted to package registries, not
university domains. Before relying on this in production: run it once
against real Aurora with --verbose, inspect the actual response shape,
and adjust the endpoint paths/params here if UManitoba's deployment
differs from the documented convention.
"""

from __future__ import annotations

import logging
import random
import re
import string
import time
from collections.abc import Iterator
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings

logger = logging.getLogger(__name__)

PAGE_MAX_SIZE = 500
REQUEST_TIMEOUT_SECONDS = 30.0

# Page size for the getTerms JSON endpoint. Kept separate from
# PAGE_MAX_SIZE (which governs /searchResults section paging) since
# Banner treats these as independent, differently-sized endpoints --
# getTerms' own UI (Select2) defaults to a page of 50 as well.
TERMS_PAGE_MAX_SIZE = 50

# Page size for the get_subject JSON endpoint. A university the size of
# UManitoba has on the order of a few hundred subjects, so this is
# generous headroom while still keeping each page small.
SUBJECTS_PAGE_MAX_SIZE = 100

# Aurora's term codes are Banner's standard 6-digit YYYY+suffix convention
# (e.g. "202690"). Used to defensively filter out any non-term <option>
# Aurora's markup might include (a blank "Select a Term" placeholder, a
# disabled separator, etc.) rather than trusting every <option> blindly.
_TERM_CODE_PATTERN = re.compile(r"^\d{6}$")

# getTerms returns Aurora's full rolling history (back to 2006), far more
# than the planner needs. Term codes are zero-padded 6-digit strings
# (YYYY + suffix, e.g. "202390" = Fall 2023), so as long as both sides are
# the same width, ordinary string comparison sorts them the same as
# numeric comparison -- no int() conversion needed. Anything older than
# this is skipped entirely rather than fetched and discarded later.
MIN_TERM_CODE = "202390"  # Fall 2023

# Terms ending in "80" are UManitoba's PGME (Post-Graduate Medical
# Education) residency terms, which run on a separate academic calendar
# and aren't relevant to the planner -- skipped alongside the
# MIN_TERM_CODE filter above.
_PGME_TERM_SUFFIX = "80"


# Banner 9 keys its advanced search filters (like txt_subject) to a
# uniqueSessionId rather than just the session cookie -- confirmed by
# inspecting the browser's network payload against live Aurora. Without
# it, /searchResults/searchResults silently ignores txt_subject and just
# returns the same default batch for every subject. This must be sent to
# BOTH /term/search (_select_term) and /searchResults/searchResults
# (_fetch_page).
#
# A captured real session ID looked like "br6qm1784476359558" -- a 5-char
# lowercase-alphanumeric prefix followed by a 13-digit epoch-millisecond
# timestamp, which is exactly what Banner's own front-end JS generates
# client-side per page load. This mirrors that format rather than
# hardcoding the literal captured value: a copied snapshot is tied to
# someone else's already-closed browser session and stamped with a
# timestamp from the past, so there's no guarantee Banner accepts it
# outside the moment it was captured -- and reusing one fixed string
# across every run/subject means concurrent importer runs would collide
# on the same ID, which is exactly the class of bug we're chasing here.
# Generating a fresh one per AuroraClient instance and reusing it for
# that instance's whole session (same as the browser does per page load)
# gets the realistic format without either risk.
def _generate_unique_session_id() -> str:
    prefix = "".join(random.choices(string.ascii_lowercase + string.digits, k=5))
    epoch_ms = int(time.time() * 1000)
    return f"{prefix}{epoch_ms}"


# Best-effort patterns for a synchronizer token embedded in page HTML/JS
# rather than a response header. Confirmed via reading Banner's own
# unminified JS (bannerWeb-mf.unminified.js): jQuery's ajaxPrefilter reads
# `<meta name="synchronizerToken" content="...">` out of the page DOM on
# every AJAX call and stamps it onto the request as X-Synchronizer-Token
# -- so it's rendered once into the page HTML per session/page-load, not
# returned via a response header at all, which is exactly why the
# header-only check never found it. The meta-tag pattern is written
# attribute-order-agnostic (via lookaheads) rather than assuming
# `name` always precedes `content`, since that's an HTML rendering detail
# that could change without notice. The second pattern is a fallback for
# a JS-assignment style (`synchronizerToken: "..."` / `= "..."`) in case
# some other page on the site embeds it differently.
_SYNCHRONIZER_TOKEN_BODY_PATTERNS = [
    re.compile(
        r"""<meta\b(?=[^>]*\bname=["']synchronizerToken["'])"""
        r"""(?=[^>]*\bcontent=["']([\w-]{8,})["'])[^>]*>""",
        re.IGNORECASE,
    ),
    re.compile(r"""synchronizerToken["']?\s*[:=]\s*["']([\w-]{8,})["']""", re.IGNORECASE),
]

_RETRY = retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))


class AuroraTermScrapeError(RuntimeError):
    """Raised when the getTerms endpoint can't be reached or parsed.

    Kept as its own exception (rather than a generic RuntimeError) so
    callers -- and run_importer.py's --all-terms flag -- can catch this
    specifically and fail with a clear, actionable message instead of a
    confusing downstream error."""


class AuroraSubjectScrapeError(RuntimeError):
    """Raised when the get_subject endpoint can't be reached or parsed.

    Kept separate from AuroraTermScrapeError so callers can tell which
    endpoint failed -- a broken subject list means fetch_all_sections
    can't even start iterating, which is worth distinguishing from a
    broken term list."""


class AuroraClient:
    """
    Thin wrapper around Aurora's anonymous class-search endpoints.

    Usage:
        with AuroraClient() as client:
            for term_code, description in client.fetch_available_terms():
                ...
            subjects = client.get_subjects("202690")
            for raw_section in client.fetch_all_sections("202690"):
                ...
    """

    def __init__(self, base_url: str | None = None) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.aurora_base_url).rstrip("/")
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers={
                "User-Agent": "umanitoba-planner-importer/0.1",
                # These three are present on every real browser request
                # against this endpoint and absent from ours (confirmed
                # by diffing a captured working browser request). Adding
                # them is a straightforward, honest fix -- any legitimate
                # AJAX client reasonably sends these -- unlike spoofing a
                # full Chrome fingerprint (sec-ch-ua, exact browser UA),
                # which this deliberately stops short of; see the
                # X-Synchronizer-Token note below for why that one can't
                # be fixed the same simple way.
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": f"{self.base_url}/classSearch/classSearch",
            },
            follow_redirects=True,
        )
        # Generated once per client instance and reused for every request
        # this instance makes (same as the browser generates one per page
        # load and reuses it for that session) -- see _generate_unique_session_id.
        self._unique_session_id = _generate_unique_session_id()
        # Populated by _capture_synchronizer_token if/when Banner exposes
        # one -- see that method's docstring for the caveats.
        self._synchronizer_token: str | None = None

    def __enter__(self) -> AuroraClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    # -- session handshake ---------------------------------------------------

    @_RETRY
    def _init_session(self) -> None:
        """Visit the search page once to establish Banner's session cookie."""
        resp = self._client.get("/classSearch/classSearch")
        resp.raise_for_status()
        self._capture_synchronizer_token(resp, source="/classSearch/classSearch")

    def _capture_synchronizer_token(self, resp: httpx.Response, source: str) -> None:
        """
        Best-effort extraction of Banner's X-Synchronizer-Token (a Spring
        Security synchronizer-token/CSRF pattern -- confirmed present on
        every real browser request against /searchResults, absent from
        this client's requests, and a very plausible explanation for
        requests silently falling back to a fixed default result set
        instead of erroring outright).

        This has NOT been verified against live Aurora. It checks two
        candidate locations: the response header (confirmed absent on both
        /classSearch/classSearch and /term/search per a real run) and now
        also the response body, in case Banner embeds it in the page
        HTML/JS instead -- e.g. `<meta name="synchronizerToken"
        content="...">` or a `synchronizerToken = "..."` JS assignment.
        Both came back empty on both endpoints checked so far, which is
        itself informative: it suggests the token may not be
        server-issued via either of these two channels at all -- possibly
        generated entirely client-side (like uniqueSessionId) in Banner's
        own JS bundle, in which case no amount of response-scanning here
        will ever find it, and the actual generation logic needs to be
        read directly out of that JS. See the note in the docstring for
        fetch_all_sections and the accompanying chat message for exactly
        what to look for there.
        """
        token = resp.headers.get("X-Synchronizer-Token")
        if not token:
            for pattern in _SYNCHRONIZER_TOKEN_BODY_PATTERNS:
                match = pattern.search(resp.text)
                if match:
                    token = match.group(1)
                    break

        if token:
            self._synchronizer_token = token
            self._client.headers["X-Synchronizer-Token"] = token
            logger.info("Captured X-Synchronizer-Token from %s", source)
        elif self._synchronizer_token is None:
            logger.warning(
                "No X-Synchronizer-Token found in the %s response header or body. This "
                "token may be generated entirely client-side by Banner's own JS rather "
                "than issued by the server at all -- see chat for how to confirm this "
                "directly from the JS source.",
                source,
            )

    @_RETRY
    def _select_term(self, term_code: str) -> None:
        """Tell Banner which term subsequent /searchResults calls should apply to."""
        resp = self._client.post(
            "/term/search?mode=search",
            data={
                "term": term_code,
                "studyPath": "",
                "studyPathText": "",
                "startDatepicker": "",
                "endDatepicker": "",
                "uniqueSessionId": self._unique_session_id,
            },
        )
        resp.raise_for_status()
        self._capture_synchronizer_token(resp, source="/term/search")

    # -- term discovery ------------------------------------------------------

    @_RETRY
    def _fetch_terms_page(self, offset: int, max_size: int) -> list[dict[str, Any]]:
        """
        GET one page of the Banner 9 JSON terms endpoint.

        UManitoba's term-selection page renders its Select2 widget from
        this endpoint rather than a plain <select>, so term discovery goes
        straight to the JSON API instead of scraping rendered HTML. Each
        entry in the returned list looks like
        `{"code": "202690", "description": "Fall 2026", ...}`.
        """
        resp = self._client.get(
            "/classSearch/getTerms",
            params={"searchTerm": "", "offset": offset, "max": max_size},
        )
        resp.raise_for_status()
        return resp.json()

    def fetch_available_terms(self) -> list[tuple[str, str]]:
        """
        Query Aurora's getTerms JSON endpoint and return every
        (term_code, description) pair it currently offers, e.g.
        [("202690", "Fall 2026"), ("202710", "Winter 2027"), ...].

        Banner 9's Select2-based term picker populates itself from
        `StudentRegistrationSsb/ssb/classSearch/getTerms?searchTerm=&offset=1&max=50`
        rather than a server-rendered <select>, so this pages through that
        endpoint (Banner's own UI uses a page size of 50) until a page
        comes back short of `max_size`, which signals the last page.

        A session is established first (mirroring the browser, which
        always hits classSearch before its term widget loads) since some
        Banner 9 deployments key getTerms off the session cookie set there.

        Terms older than MIN_TERM_CODE are skipped entirely -- getTerms
        returns Aurora's full history back to 2006, which is far more than
        the planner needs, so this filters it down before returning rather
        than making callers filter downstream. PGME (medical residency)
        terms -- identifiable by a "80" code suffix -- are skipped for the
        same reason; they run on a separate calendar out of scope here.

        Only the network fetch is retried (transient connection issues are
        worth retrying); a response-shape mismatch is a permanent problem
        no retry will fix, so validation happens outside the retry wrapper
        and raises AuroraTermScrapeError immediately.

        Also note: however many terms getTerms lists is exactly how many
        this returns -- Banner registration UIs typically only list a
        rolling window of relevant terms (recent past + current + near
        future), not full institutional history, but that's Aurora's
        choice to make, not something this method second-guesses.
        """
        self._init_session()

        terms: list[tuple[str, str]] = []
        seen_codes: set[str] = set()
        skipped = 0
        skipped_too_old = 0
        skipped_pgme = 0
        offset = 1

        while True:
            page = self._fetch_terms_page(offset, TERMS_PAGE_MAX_SIZE)

            if not isinstance(page, list):
                raise AuroraTermScrapeError(
                    "getTerms returned an unexpected response shape (expected a JSON "
                    f"list of term objects, got {type(page).__name__}). Aurora's response "
                    "format may differ from the standard Banner 9 convention this client "
                    "assumes -- inspect the real response and update "
                    "AuroraClient.fetch_available_terms()."
                )

            if not page:
                break

            for entry in page:
                code = str(entry.get("code") or "").strip()
                label = str(entry.get("description") or "").strip()

                if not code or not _TERM_CODE_PATTERN.match(code):
                    # Skips any non-term entry (e.g. a "None" placeholder
                    # row) rather than assuming every object is a usable
                    # term.
                    skipped += 1
                    continue

                if code < MIN_TERM_CODE:
                    # Skips Aurora's older terms (getTerms lists its full
                    # rolling history back to 2006) rather than fetching
                    # and discarding them downstream.
                    skipped_too_old += 1
                    continue

                if code.endswith(_PGME_TERM_SUFFIX):
                    # Skips PGME (medical residency) terms -- they're on
                    # a separate calendar and out of scope for the planner.
                    skipped_pgme += 1
                    continue

                if code in seen_codes:
                    # Defensive: don't double-count a term if pagination
                    # ever overlaps across pages.
                    continue

                seen_codes.add(code)
                terms.append((code, label))

            if len(page) < TERMS_PAGE_MAX_SIZE:
                # A short page means we've reached the end.
                break

            offset += TERMS_PAGE_MAX_SIZE

        if skipped:
            logger.info("Skipped %d non-term entries from getTerms", skipped)

        if skipped_too_old:
            logger.info(
                "Skipped %d terms older than %s from getTerms", skipped_too_old, MIN_TERM_CODE
            )

        if skipped_pgme:
            logger.info("Skipped %d PGME terms from getTerms", skipped_pgme)

        if not terms:
            raise AuroraTermScrapeError(
                "getTerms responded successfully but contained zero valid 6-digit term "
                "codes -- Aurora's term object format may have changed."
            )

        logger.info("Discovered %d terms from Aurora: %s", len(terms), [c for c, _ in terms])
        return terms

    # -- subject discovery ----------------------------------------------------

    @_RETRY
    def _fetch_subjects_page(
        self, term_code: str, search_term: str, offset: int, max_size: int
    ) -> list[dict[str, Any]]:
        """
        GET one page of the Banner 9 JSON subjects endpoint for a given term.

        Each entry in the returned list looks like
        `{"code": "MECH", "description": "Mechanical Engineering", ...}`.

        `search_term` is Banner's own filter for this endpoint -- normally
        used to power the live type-ahead on the subject dropdown in
        Aurora's UI. See get_subjects() for why this client now sweeps
        through search_term values instead of leaving it blank: a blank
        search_term hits a hard, offset-independent cap on this endpoint
        (confirmed directly against live Aurora -- see get_subjects()'s
        docstring), silently truncating the subject list.
        """
        resp = self._client.get(
            "/classSearch/get_subject",
            params={
                "searchTerm": search_term,
                "term": term_code,
                "offset": offset,
                "max": max_size,
                # Same discovery as _select_term/_fetch_page: Banner keys
                # this session's active search context to uniqueSessionId,
                # not just the cookie. Without it, get_subject may not
                # reliably see the term selected moments earlier and can
                # fall back to some other (often much smaller) default set.
                "uniqueSessionId": self._unique_session_id,
            },
        )
        resp.raise_for_status()
        return resp.json()

    def get_subjects(self, term_code: str) -> list[str]:
        """
        Return every subject code Aurora offers for `term_code`, e.g.
        ["ACC", "MATH", "MECH", ...].

        `/searchResults/searchResults` truncates a blank-search catalog
        query at an internal record limit (observed around 3,907 records),
        so fetch_all_sections queries one subject at a time via
        `txt_subject` instead of one blank query for the whole term. This
        method is what supplies that list of subjects, from Banner 9's
        `/classSearch/get_subject` endpoint.

        IMPORTANT -- discovered directly against live Aurora, not just
        inferred from docs: this endpoint's `offset`/`max` parameters are
        NOT reliable pagination. A blank `searchTerm` query for a term
        with more than SUBJECTS_PAGE_MAX_SIZE (100) real subjects returns
        exactly the first 100 and stops there; requesting a further page
        via `offset` (tried both 1-indexed and 0-indexed continuations)
        returns an EMPTY list even though more subjects genuinely exist.
        This is what silently dropped PHYS (and everything alphabetically
        near it) for terms with 100+ subjects -- UManitoba comfortably
        exceeds 100 active subjects in a normal Fall/Winter term, so this
        bug was live for essentially every full-catalog import, not an
        edge case.

        The fix used here doesn't rely on offset at all: it sweeps
        `searchTerm` through every letter A-Z, merging and deduping
        results the same way pagination used to. Banner's matching
        against searchTerm doesn't appear to be a strict code-prefix match
        (e.g. searchTerm="PH" also returned EDUC/GEOG/KPER, which don't
        start with "PH" -- likely matching against description text too),
        which is fine: this method doesn't depend on understanding
        Banner's exact matching rule, only on the empirical fact that
        every single-letter sweep observed so far returns well under 100
        results. As a safety net against a future term where some letter's
        result set is ITSELF capped at exactly max_size (i.e. the same
        truncation bug recurring one level down), any branch that returns
        a full page recurses by appending each letter to that search term
        and searching again, up to a small depth limit -- this makes the
        method self-correcting rather than silently wrong if UManitoba's
        catalog grows.

        IMPORTANT: this does NOT call _init_session()/_select_term() itself
        -- it relies on the caller (fetch_all_sections) having already
        established the session and selected `term_code` moments earlier.
        An earlier version of this method called _init_session() again
        here, which re-GETs /classSearch/classSearch -- on Banner, loading
        that page initializes a fresh search context, which can reset the
        term selection just made and cause get_subject to silently fall
        back to some other (often much smaller) default subject set. That
        looks like exactly what produced the "34 sections total for the
        whole term" symptom: only one subject's worth of real data came
        back instead of the full catalog. If you call get_subjects()
        directly rather than through fetch_all_sections, call
        _init_session() and _select_term(term_code) yourself first.

        Only the network fetch is retried; a response-shape mismatch is a
        permanent problem no retry will fix, so validation happens outside
        the retry wrapper and raises AuroraSubjectScrapeError immediately.
        """
        subjects: list[str] = []
        seen_codes: set[str] = set()

        # How many extra letters a search term is allowed to grow by if a
        # branch keeps coming back full -- e.g. "A" -> "AB" -> "ABC".
        # Three levels comfortably covers any realistic catalog size
        # without risking runaway recursion on unexpected data.
        _MAX_SWEEP_DEPTH = 3

        def sweep(search_term: str, depth: int) -> None:
            page = self._fetch_subjects_page(term_code, search_term, offset=1, max_size=SUBJECTS_PAGE_MAX_SIZE)

            if not isinstance(page, list):
                raise AuroraSubjectScrapeError(
                    "get_subject returned an unexpected response shape (expected a JSON "
                    f"list of subject objects, got {type(page).__name__}) for term "
                    f"{term_code} (searchTerm={search_term!r}). Aurora's response format "
                    "may differ from the standard Banner 9 convention this client assumes "
                    "-- inspect the real response and update AuroraClient.get_subjects()."
                )

            for entry in page:
                code = str(entry.get("code") or "").strip()
                if not code or code in seen_codes:
                    continue
                seen_codes.add(code)
                subjects.append(code)

            if len(page) >= SUBJECTS_PAGE_MAX_SIZE:
                if depth >= _MAX_SWEEP_DEPTH:
                    logger.warning(
                        "Term %s: searchTerm=%r still returned a full page at max sweep "
                        "depth (%d) -- some subjects may be missing. Increase "
                        "_MAX_SWEEP_DEPTH in get_subjects() if this keeps happening.",
                        term_code,
                        search_term,
                        _MAX_SWEEP_DEPTH,
                    )
                    return
                for letter in string.ascii_uppercase:
                    sweep(search_term + letter, depth + 1)

        for letter in string.ascii_uppercase:
            sweep(letter, depth=1)

        if not subjects:
            raise AuroraSubjectScrapeError(
                f"get_subject responded successfully but contained zero valid subject "
                f"codes for term {term_code} -- Aurora's subject object format may have "
                "changed."
            )

        # A real university offers well over 100 subjects in an active term.
        # A suspiciously short list here (rather than an outright error) is
        # exactly the failure mode that produced the "34 sections total"
        # symptom, so surface it loudly instead of silently importing a
        # near-empty catalog.
        if len(subjects) < 20:
            logger.warning(
                "Term %s: get_subject only returned %d subject(s) (%s) -- a real term "
                "should have 100+. This term's import is almost certainly incomplete; "
                "see the note in AuroraClient.get_subjects() about session/term state.",
                term_code,
                len(subjects),
                subjects,
            )

        logger.info("Term %s: discovered %d subjects", term_code, len(subjects))
        return sorted(subjects)

    # -- paginated fetch -------------------------------------------------------

    @_RETRY
    def _reset_search_form(self) -> None:
        """
        GET /classSearch/resetDataForm -- clears Banner's server-side stored
        search criteria before starting a NEW subject's search.

        Evidence this is needed: after confirming X-Synchronizer-Token is
        being captured and sent correctly (no more effect than before --
        totalCount stayed IDENTICAL across every subject within a term:
        32 for every subject in term 202710, 34 for every subject in term
        202390, always ACC's records), the token theory is ruled out. But
        that exact symptom -- every subject search returning the SAME
        fixed result, matching whichever subject was queried FIRST
        alphabetically (ACC) -- fits a different explanation: Banner may
        be storing search criteria server-side keyed to the session
        rather than re-parsing txt_subject fresh out of the query string
        on every call. If so, the first search sets the server-side
        state and every later /searchResults call just replays it,
        regardless of what the URL says. A real user doesn't hit this
        because the browser resets that stored state before each new
        search click -- this reproduces that reset.

        NOT yet verified against live Aurora. If totalCount still doesn't
        vary by subject after adding this call, this theory is wrong too
        and needs to be ruled out the same way the token was: report back
        with a fresh totalCount= sample and this gets crossed off the list.
        """
        resp = self._client.get("/classSearch/resetDataForm")
        resp.raise_for_status()

    @_RETRY
    def _fetch_page(self, term_code: str, page_offset: int, subject_code: str) -> dict[str, Any]:
        params = {
            "txt_subject": subject_code,
            "txt_term": term_code,
            # Present (but empty) in the captured browser payload for a
            # filtered search.
            "startDatepicker": "",
            "endDatepicker": "",
            "uniqueSessionId": self._unique_session_id,
            "pageOffset": page_offset,
            "pageMaxSize": PAGE_MAX_SIZE,
            "sortColumn": "subjectDescription",
            "sortDirection": "asc",
        }
        resp = self._client.get("/searchResults/searchResults", params=params)
        resp.raise_for_status()
        return resp.json()

    def fetch_all_sections(self, term_code: str) -> Iterator[dict[str, Any]]:
        """
        Yield every raw section record Aurora has for `term_code`.

        A blank-search query (no txt_subject) silently truncates at
        Aurora's internal record limit (observed around 3,907 records) --
        it doesn't set totalCount to signal the truncation, it just stops
        returning data early. To get the full catalog, this instead calls
        get_subjects() to enumerate every subject for the term, then runs
        one paginated /searchResults query per subject with txt_subject
        set, walking pageOffset by PAGE_MAX_SIZE within each subject until
        that subject's own totalCount is reached.

        Sections cross-listed under more than one subject (e.g. a joint
        Math/Stats course) could otherwise be yielded twice, once per
        subject it's filed under -- courseReferenceNumber (CRN) is unique
        per section, so it's used to deduplicate across subjects.
        """
        self._init_session()
        self._select_term(term_code)

        subjects = self.get_subjects(term_code)
        logger.info("Term %s: fetching sections for %d subjects", term_code, len(subjects))

        # Maps crn -> the subject_code it was FIRST seen under, so that if a
        # later subject turns out to be 100% duplicates, we can say exactly
        # which earlier subject it collided with -- strong, specific
        # evidence for "txt_subject isn't actually being applied" rather
        # than the more common (and harmless) case of one or two
        # legitimately cross-listed courses.
        seen_crns: dict[str, str] = {}
        total_yielded = 0

        # Subjects where every retry still came back 100% duplicates --
        # i.e. we never got that subject's real data at all. Surfaced to
        # the caller so an incomplete import fails loudly instead of
        # silently shipping a term with a subject missing every section.
        failed_subjects: list[str] = []

        MAX_SUBJECT_ATTEMPTS = 3

        for subject_code in subjects:
            for attempt in range(1, MAX_SUBJECT_ATTEMPTS + 1):
                self._reset_search_form()
                if attempt > 1:
                    # The previous attempt's reset apparently hadn't taken
                    # effect server-side yet (see _reset_search_form) --
                    # give Banner a moment before hitting it again.
                    time.sleep(1.5 * attempt)

                offset = 0
                fetched = 0
                total_count: int | None = None
                subject_new_count = 0
                subject_duplicate_count = 0
                duplicate_of: set[str] = set()
                pending_records: list[dict[str, Any]] = []

                while total_count is None or fetched < total_count:
                    payload = self._fetch_page(term_code, offset, subject_code)

                    if payload.get("success") is False:
                        logger.warning(
                            "Aurora reported success=False for term %s subject %s at offset %d",
                            term_code,
                            subject_code,
                            offset,
                        )
                        break

                    records: list[dict[str, Any]] = payload.get("data") or []
                    if total_count is None:
                        total_count = payload.get("totalCount", len(records))
                        logger.info(
                            "Term %s subject %s: totalCount=%s",
                            term_code,
                            subject_code,
                            total_count,
                        )

                    if not records:
                        break

                    for record in records:
                        crn = record.get("courseReferenceNumber")
                        if crn is not None:
                            if crn in seen_crns:
                                subject_duplicate_count += 1
                                duplicate_of.add(seen_crns[crn])
                                continue
                            subject_new_count += 1
                        pending_records.append(record)

                    fetched += len(records)
                    offset += PAGE_MAX_SIZE
                    logger.info(
                        "Term %s subject %s: fetched %d/%s",
                        term_code,
                        subject_code,
                        fetched,
                        total_count,
                    )

                if fetched > 0 and subject_new_count == 0:
                    # Every single record this subject returned was already
                    # seen under a different subject -- a couple of overlaps
                    # is normal for genuinely cross-listed courses, but ALL
                    # of them matching is a strong signal Banner replayed a
                    # stale cached result instead of applying txt_subject.
                    if attempt < MAX_SUBJECT_ATTEMPTS:
                        logger.warning(
                            "Term %s subject %s: attempt %d/%d -- ALL %d fetched record(s) "
                            "were duplicates of %s. Retrying after a fresh reset.",
                            term_code,
                            subject_code,
                            attempt,
                            MAX_SUBJECT_ATTEMPTS,
                            subject_duplicate_count,
                            sorted(duplicate_of),
                        )
                        continue  # retry this subject
                    logger.warning(
                        "Term %s subject %s: attempt %d/%d -- ALL %d fetched record(s) "
                        "were duplicates of %s. Giving up on this subject for this term; "
                        "its sections were NOT imported.",
                        term_code,
                        subject_code,
                        attempt,
                        MAX_SUBJECT_ATTEMPTS,
                        subject_duplicate_count,
                        sorted(duplicate_of),
                    )
                    failed_subjects.append(subject_code)
                    break  # out of attempts, move to next subject

                # Success (or a genuinely empty subject) -- commit this
                # attempt's records and stop retrying.
                for record in pending_records:
                    crn = record.get("courseReferenceNumber")
                    if crn is not None:
                        seen_crns[crn] = subject_code
                    yield record
                    total_yielded += 1
                break

        if failed_subjects:
            raise RuntimeError(
                f"Term {term_code}: {len(failed_subjects)} subject(s) never returned real "
                f"data after {MAX_SUBJECT_ATTEMPTS} attempts each (still 100% duplicates of "
                f"an earlier subject): {sorted(failed_subjects)}. These subjects' sections "
                "were NOT imported for this term -- rerun the import for this term, or "
                "investigate why Banner keeps replaying a stale result for them."
            )

        logger.info(
            "Term %s: yielded %d total sections across all subjects", term_code, total_yielded
        )
        if total_yielded < 500:
            logger.warning(
                "Term %s: only %d sections total across %d subjects -- a real term "
                "usually has several thousand. This import is very likely incomplete; "
                "check the per-subject 'totalCount=' log lines above to see whether most "
                "subjects came back empty.",
                term_code,
                total_yielded,
                len(subjects),
            )
