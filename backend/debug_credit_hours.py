"""
Prints Aurora's raw JSON for every MECH 2222 section in term 202690 --
mapper.py already checks both `creditHours` and `creditHourLow`, and
credit_hours is still landing as 0 in the DB for this course, so this
looks at the actual raw payload to see what Aurora is really sending
(a different field name entirely? genuinely absent on every section?).

Run from the backend/ directory with the venv active:

    python debug_credit_hours.py
"""

import json

from app.importer.aurora_client import AuroraClient

TERM_CODE = "202690"

with AuroraClient() as client:
    for raw in client.fetch_all_sections(TERM_CODE):
        if raw.get("subject") == "MECH" and str(raw.get("courseNumber")) == "2222":
            print(json.dumps(raw, indent=2))
