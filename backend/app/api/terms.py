from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Term
from app.schemas import TermRead

router = APIRouter(prefix="/terms", tags=["terms"])


@router.get("", response_model=list[TermRead])
def list_terms(db: Session = Depends(get_db)) -> list[Term]:
    """All terms currently imported, most recent first."""
    stmt = select(Term).order_by(Term.term_code.desc())
    return db.execute(stmt).scalars().all()
