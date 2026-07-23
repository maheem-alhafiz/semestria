"""
Database engine and session management.

Single source of truth for how the app talks to Postgres. Models import
`Base` from here; routers/services import `get_db` as a FastAPI dependency.
"""

from collections.abc import Generator

from sqlalchemy import MetaData
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy import create_engine

from app.core.config import get_settings

settings = get_settings()

# A fixed naming convention means Alembic autogenerate produces stable,
# predictable constraint/index names (e.g. "fk_sections_course_id_courses")
# instead of database-assigned ones that differ across environments and
# cause noisy diffs.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Shared declarative base for every ORM model in the app."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def _build_engine() -> Engine:
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,  # avoids using stale/dropped connections after idle periods
        future=True,
    )


engine: Engine = _build_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    future=True,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a request-scoped DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
