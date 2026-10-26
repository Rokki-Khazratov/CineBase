"""Typed errors with one body shape: {error: {code, message, fields?, request_id}} (TECHNICAL_SPEC §5)."""

import logging
import re
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("cinebase.api")

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
_INCOMING_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, fields: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.fields = fields


def not_found(code: str, message: str) -> ApiError:
    return ApiError(404, code, message)


def _body(code: str, message: str, fields: dict[str, str] | None = None) -> dict[str, object]:
    error: dict[str, object] = {"code": code, "message": message, "request_id": request_id_var.get()}
    if fields:
        error["fields"] = fields
    return {"error": error}


def install(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_id(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        incoming = request.headers.get("x-request-id", "")
        rid = incoming if _INCOMING_ID.match(incoming) else f"req_{uuid.uuid4().hex[:16]}"
        token = request_id_var.set(rid)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = rid
        return response

    @app.exception_handler(ApiError)
    async def api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(_body(exc.code, exc.message, exc.fields), status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        fields: dict[str, str] = {}
        for err in exc.errors():
            loc = [str(part) for part in err.get("loc", ()) if part not in ("query", "path", "body")]
            fields[".".join(loc) or "request"] = str(err.get("msg", "Invalid value."))
        return JSONResponse(_body("invalid_parameters", "Some parameters are invalid.", fields), status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = "not_found" if exc.status_code == 404 else "http_error"
        message = "Nothing exists at this address." if exc.status_code == 404 else str(exc.detail)
        return JSONResponse(_body(code, message), status_code=exc.status_code)

    @app.exception_handler(OperationalError)
    async def db_unavailable(_: Request, exc: OperationalError) -> JSONResponse:
        log.error("database unavailable: %s", type(exc.orig).__name__ if exc.orig else "unknown")
        return JSONResponse(_body("catalog_unavailable", "The catalog is temporarily unavailable."), status_code=503)

    @app.exception_handler(DBAPIError)
    async def db_error(_: Request, exc: DBAPIError) -> JSONResponse:
        if exc.connection_invalidated:
            return JSONResponse(
                _body("catalog_unavailable", "The catalog is temporarily unavailable."), status_code=503
            )
        log.exception("database error")
        return JSONResponse(_body("internal_error", "Something went wrong on our side."), status_code=500)

    @app.exception_handler(Exception)
    async def unexpected(_: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled error", exc_info=exc)
        return JSONResponse(_body("internal_error", "Something went wrong on our side."), status_code=500)
