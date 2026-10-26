"""Tests run against a real PostgreSQL database (pg_trgm is part of what is being tested).

CINEBASE_TEST_DATABASE_URL defaults to postgresql+psycopg://localhost/cinebase_test. The schema is dropped and
migrated once per session, then seeded with the fixture catalog.
"""

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text

from cinebase_api import cli, db
from cinebase_api.main import create_app

TEST_URL = os.environ.get("CINEBASE_TEST_DATABASE_URL", "postgresql+psycopg://localhost/cinebase_test")


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    engine = create_engine(TEST_URL)
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    cli.migrate(TEST_URL)
    cli.seed_fixtures(engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def client(engine: Engine) -> Iterator[TestClient]:
    app = create_app()
    factory = db.session_factory(engine)

    def session() -> Iterator[object]:
        with factory() as s:
            yield s

    app.dependency_overrides[db.get_session] = session
    with TestClient(app) as c:
        yield c
