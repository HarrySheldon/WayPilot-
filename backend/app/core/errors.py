from __future__ import annotations

from uuid import uuid4

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


REQUEST_ID_HEADER = "x-request-id"


async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers[REQUEST_ID_HEADER] = request_id
    return response


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    request_id = _request_id(request)
    headers = dict(exc.headers or {})
    headers[REQUEST_ID_HEADER] = request_id
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_payload(
            code=_http_error_code(exc),
            message=_safe_http_message(exc),
            request_id=request_id,
        ),
        headers=headers,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id = _request_id(request)
    return JSONResponse(
        status_code=422,
        content=_error_payload(
            code="validation_error",
            message="Request validation failed",
            request_id=request_id,
        ),
        headers={REQUEST_ID_HEADER: request_id},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = _request_id(request)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_payload(
            code="internal_error",
            message="Internal server error",
            request_id=request_id,
        ),
        headers={REQUEST_ID_HEADER: request_id},
    )


def _error_payload(*, code: str, message: str, request_id: str) -> dict:
    return {"error": {"code": code, "message": message, "request_id": request_id}}


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid4()))


def _safe_http_message(exc: StarletteHTTPException) -> str:
    return exc.detail if isinstance(exc.detail, str) else "Request failed"


def _http_error_code(exc: StarletteHTTPException) -> str:
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        return "not_authenticated"
    if exc.status_code == status.HTTP_403_FORBIDDEN:
        return "forbidden"
    if exc.status_code == status.HTTP_404_NOT_FOUND and isinstance(exc.detail, str):
        normalized = exc.detail.strip().lower()
        if normalized == "trip not found":
            return "trip_not_found"
        if normalized == "agent run not found":
            return "agent_run_not_found"
        if normalized == "candidate not found":
            return "candidate_not_found"
        if normalized == "version not found":
            return "version_not_found"
        return "not_found"
    if exc.status_code == status.HTTP_409_CONFLICT:
        return "conflict"
    return "http_error"
