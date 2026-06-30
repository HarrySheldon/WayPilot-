from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .api.router import api_router
from .core.errors import (
    http_exception_handler,
    request_id_middleware,
    unhandled_exception_handler,
    validation_exception_handler,
)
from .core.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="WayPilot API", version="0.1.0")
    app.middleware("http")(request_id_middleware)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
