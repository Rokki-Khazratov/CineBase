"""CineBase catalog API. Run: uvicorn cinebase_api.main:app"""

import logging

from fastapi import FastAPI

from . import errors
from .routers import catalog, health
from .settings import get_settings


def create_app() -> FastAPI:
    logging.basicConfig(level=get_settings().log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    app = FastAPI(
        title="CineBase Catalog API",
        version="0.1.0",
        description="Read-only film catalog: search, browse, film details and credits.",
    )
    errors.install(app)
    app.include_router(health.router)
    app.include_router(catalog.router)
    return app


app = create_app()
