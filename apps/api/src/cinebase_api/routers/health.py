from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..db import get_session
from ..errors import ApiError
from ..schemas import Health

router = APIRouter(tags=["health"])


@router.get("/health/live", response_model=Health)
def live() -> Health:
    """The process is up. Does not touch the database."""
    return Health(status="ok")


@router.get("/health/ready", response_model=Health, responses={503: {"description": "Database not reachable"}})
def ready(session: Annotated[Session, Depends(get_session)]) -> Health:
    """The catalog can be queried: the database answers and the schema exists."""
    try:
        session.execute(text("SELECT 1 FROM movie LIMIT 1"))
    except Exception:
        raise ApiError(503, "catalog_unavailable", "The catalog is temporarily unavailable.") from None
    return Health(status="ok")
