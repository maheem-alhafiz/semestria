"""
One-off diagnostic: calls AuroraClient.get_subjects() directly for term
202690 and reports exactly what came back, so we can see whether PHYS is
present in the raw subject list Aurora hands back -- independent of
anything the importer's per-subject fetch loop or logging does.

Run from the backend/ directory (same place you run `python -m
app.importer.run_importer`) with the venv active:

    python debug_subjects.py
"""

from app.importer.aurora_client import AuroraClient

TERM_CODE = "202690"

with AuroraClient() as client:
    # get_subjects() doesn't establish the session/select the term itself
    # (see its docstring) -- when called outside fetch_all_sections, the
    # caller has to do that first.
    client._init_session()
    client._select_term(TERM_CODE)

    subjects = client.get_subjects(TERM_CODE)

    print(f"Total subjects returned: {len(subjects)}")
    print(f"'PHYS' in list: {'PHYS' in subjects}")
    print()
    print("Full list:")
    print(subjects)
