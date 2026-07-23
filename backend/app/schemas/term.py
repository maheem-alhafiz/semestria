from pydantic import BaseModel, ConfigDict


class TermRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    term_code: str
    description: str
