import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import (
    activities,
    board,
    config_routes,
    contacts,
    discovery,
    health,
    messages,
    partners,
    signals,
)
from app.errors import (
    Conflict,
    DomainError,
    ExternalServiceError,
    GateBlocked,
    InvalidTransition,
    NotFound,
)
from app.settings import settings

ERROR_STATUS: list[tuple[type[DomainError], int]] = [
    (NotFound, 404),
    (Conflict, 409),
    (InvalidTransition, 409),
    (GateBlocked, 422),
    (ExternalServiceError, 502),
]


def configure_logging() -> None:
    """Print the app's own progress (discovery steps, scoring, LLM calls) in the
    API terminal next to uvicorn's request log. Uvicorn only configures its own
    loggers, so without this anything below WARNING from app.* is dropped."""
    app_logger = logging.getLogger("app")
    if not app_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)-8s %(name)s: %(message)s"))
        app_logger.addHandler(handler)
    app_logger.setLevel(settings.log_level)
    # Uvicorn's root has no handler; don't also bubble up and print twice elsewhere.
    app_logger.propagate = False


def create_app() -> FastAPI:
    configure_logging()
    application = FastAPI(title="INSURVAS Partner Pipeline", version="0.1.0", docs_url="/docs")

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api_prefix = "/api/v1"
    application.include_router(health.router, prefix=api_prefix)
    application.include_router(config_routes.router, prefix=api_prefix)
    application.include_router(partners.router, prefix=api_prefix)
    application.include_router(signals.router, prefix=api_prefix)
    application.include_router(contacts.router, prefix=api_prefix)
    application.include_router(messages.router, prefix=api_prefix)
    application.include_router(activities.router, prefix=api_prefix)
    application.include_router(discovery.router, prefix=api_prefix)
    application.include_router(board.router, prefix=api_prefix)

    @application.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError):
        status = next((code for cls, code in ERROR_STATUS if isinstance(exc, cls)), 500)
        return JSONResponse(
            status_code=status,
            content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
        )

    return application


app = create_app()
