"""
One-off diagnostic: after establishing a session and selecting term
202690 (same as debug_subjects.py), this calls the raw, private
_fetch_subjects_page() directly for offset=101 -- i.e. exactly the second
page get_subjects() would request right after a full 100-item first page
-- and prints exactly what Banner sends back, unfiltered and undeduped.

This exists to answer one question: does Banner's /classSearch/get_subject
endpoint actually have more subjects beyond the first 100, and if so, what
does the raw response for page 2 actually look like (short list? empty
list? something malformed that "if not page: break" or "len(page) < 100"
would misinterpret as end-of-data)?

Run from the backend/ directory with the venv active:

    python debug_subjects_page2.py
"""

from app.importer.aurora_client import AuroraClient, SUBJECTS_PAGE_MAX_SIZE

TERM_CODE = "202690"

with AuroraClient() as client:
    client._init_session()
    client._select_term(TERM_CODE)

    print(f"Requesting page 2: offset=101, max={SUBJECTS_PAGE_MAX_SIZE}")
    page2 = client._fetch_subjects_page(TERM_CODE, offset=101, max_size=SUBJECTS_PAGE_MAX_SIZE)

    print(f"Raw type: {type(page2).__name__}")
    print(f"Raw length: {len(page2) if hasattr(page2, '__len__') else 'n/a'}")
    print("Raw content:")
    print(page2)

    print()
    print("--- Also trying offset=100 (in case Banner's offset is 0-indexed, not 1-indexed) ---")
    page2_zero_indexed = client._fetch_subjects_page(
        TERM_CODE, offset=100, max_size=SUBJECTS_PAGE_MAX_SIZE
    )
    print(f"Raw length: {len(page2_zero_indexed) if hasattr(page2_zero_indexed, '__len__') else 'n/a'}")
    print(page2_zero_indexed)
