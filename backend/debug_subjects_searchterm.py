"""
Tests whether passing a non-blank `searchTerm` to /classSearch/get_subject
returns a filtered (and therefore smaller, sub-100) result set instead of
the same capped-at-100 list we get with a blank searchTerm. If Banner's
100-item cap applies per-query rather than being an absolute hard limit on
the endpoint, filtering by letter should let us discover every subject by
making several small queries instead of one that silently truncates.

Run from the backend/ directory with the venv active:

    python debug_subjects_searchterm.py
"""

from app.importer.aurora_client import AuroraClient, SUBJECTS_PAGE_MAX_SIZE

TERM_CODE = "202690"

with AuroraClient() as client:
    client._init_session()
    client._select_term(TERM_CODE)

    for term in ["P", "PH", "M"]:
        page = client._fetch_subjects_page(TERM_CODE, offset=1, max_size=SUBJECTS_PAGE_MAX_SIZE)
        # NOTE: _fetch_subjects_page doesn't currently accept searchTerm --
        # calling the underlying HTTP request directly here instead so we
        # can pass it without modifying the client yet.
        resp = client._client.get(
            "/classSearch/get_subject",
            params={
                "searchTerm": term,
                "term": TERM_CODE,
                "offset": 1,
                "max": SUBJECTS_PAGE_MAX_SIZE,
                "uniqueSessionId": client._unique_session_id,
            },
        )
        resp.raise_for_status()
        results = resp.json()
        codes = [entry.get("code") for entry in results]
        print(f"searchTerm={term!r}: {len(results)} result(s)")
        print(f"  PHYS present: {'PHYS' in codes}")
        print(f"  codes: {codes}")
        print()
