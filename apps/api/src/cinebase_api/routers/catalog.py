from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from .. import catalog, schemas
from ..db import get_session
from ..errors import ApiError
from ..query import DEFAULT_LIMIT, MAX_LIMIT, parse_movie_query

router = APIRouter(prefix="/api/v1", tags=["catalog"])
SessionDep = Annotated[Session, Depends(get_session)]

ERRORS: dict[int | str, dict[str, object]] = {
    400: {"model": schemas.ErrorBody, "description": "Invalid cursor"},
    404: {"model": schemas.ErrorBody, "description": "Not found"},
    422: {"model": schemas.ErrorBody, "description": "Invalid parameters"},
    503: {"model": schemas.ErrorBody, "description": "Catalog unavailable"},
}
# Catalog data changes only on import; short shared caching keeps browse pages cheap.
CACHE = "public, max-age=60"


@router.get("/movies", response_model=schemas.MoviePage, responses=ERRORS)
def list_movies(
    session: SessionDep,
    response: Response,
    q: Annotated[str | None, Query(description="Title search, any language. 'Title (YYYY)' prefers that year.")] = None,
    genre: Annotated[list[str], Query(description="Genre slug; repeat or comma-separate for any-of.")] = [],  # noqa: B006
    year_from: str | None = None,
    year_to: str | None = None,
    runtime_max: Annotated[str | None, Query(description="Maximum runtime in minutes.")] = None,
    exclude: Annotated[list[str], Query(description="Hide: short, tv, documentary, unreleased.")] = [],  # noqa: B006
    sort: Annotated[schemas.Sort | None, Query()] = None,
    limit: Annotated[str | None, Query(description=f"1–{MAX_LIMIT}, default {DEFAULT_LIMIT}.")] = None,
    cursor: str | None = None,
) -> schemas.MoviePage:
    query = parse_movie_query(q, genre, year_from, year_to, runtime_max, exclude, sort, limit, cursor)
    response.headers["Cache-Control"] = CACHE
    return catalog.list_movies(session, query)


@router.get("/movies/{movie_id}", response_model=schemas.MovieDetail, responses=ERRORS)
def get_movie(movie_id: str, session: SessionDep, response: Response) -> schemas.MovieDetail:
    response.headers["Cache-Control"] = CACHE
    return catalog.get_movie(session, movie_id)


@router.get("/movies/{movie_id}/credits", response_model=schemas.MovieCredits, responses=ERRORS)
def get_credits(movie_id: str, session: SessionDep, response: Response) -> schemas.MovieCredits:
    response.headers["Cache-Control"] = CACHE
    return catalog.get_credits(session, movie_id)


@router.get("/genres", response_model=list[schemas.GenreRef], responses=ERRORS)
def list_genres(session: SessionDep, response: Response) -> list[schemas.GenreRef]:
    response.headers["Cache-Control"] = CACHE
    return catalog.list_genres(session)


@router.get("/collections", response_model=list[schemas.Collection], responses=ERRORS)
def list_collections(session: SessionDep) -> list[schemas.Collection]:
    return catalog.list_collections(session)


@router.get("/collections/{slug}", response_model=schemas.Collection, responses=ERRORS)
def get_collection(slug: str, session: SessionDep) -> schemas.Collection:
    return catalog.get_collection(session, slug)


@router.get("/collections/{slug}/movies", response_model=schemas.MoviePage, responses=ERRORS)
def collection_movies(slug: str, session: SessionDep) -> schemas.MoviePage:
    return catalog.collection_movies(session, slug)


@router.get("/discover", response_model=schemas.Discover, responses=ERRORS)
def discover(session: SessionDep, response: Response) -> schemas.Discover:
    response.headers["Cache-Control"] = CACHE
    return catalog.discover(session)


@router.get("/catalog", response_model=schemas.CatalogInfo, responses=ERRORS)
def catalog_info(session: SessionDep) -> schemas.CatalogInfo:
    return catalog.catalog_info(session)


@router.get("/people/{person_id}", response_model=schemas.Person, responses=ERRORS)
def get_person(person_id: str, session: SessionDep) -> schemas.Person:
    return catalog.get_person(session, person_id)


@router.get("/people/{person_id}/movies", response_model=schemas.PersonMoviePage, responses=ERRORS)
def person_movies(
    person_id: str, session: SessionDep, limit: int = DEFAULT_LIMIT, cursor: str | None = None
) -> schemas.PersonMoviePage:
    if not 1 <= limit <= MAX_LIMIT:
        raise ApiError(422, "invalid_parameters", "Some parameters are invalid.", {"limit": f"1–{MAX_LIMIT}"})
    return catalog.person_movies(session, person_id, limit, cursor)
