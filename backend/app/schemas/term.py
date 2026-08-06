from datetime import date

from pydantic import BaseModel, ConfigDict


class TermRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    term_code: str
    description: str
    # Derived, may be null for a term with no imported sections yet -- see
    # app.models.term's docstring.
    start_date: date | None = None
    end_date: date | None = None
