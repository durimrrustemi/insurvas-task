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
from app.errors import Conflict, DomainError, GateBlocked, InvalidTransition, NotFound


def create_app() -> FastAPI:
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

    @application.exception_handler(NotFound)
    async def not_found_handler(request: Request, exc: NotFound):
        return JSONResponse(
            status_code=404,
            content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
        )

    @application.exception_handler(Conflict)
    async def conflict_handler(request: Request, exc: Conflict):
        return JSONResponse(
            status_code=409,
            content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
        )

    @application.exception_handler(InvalidTransition)
    async def invalid_transition_handler(request: Request, exc: InvalidTransition):
        return JSONResponse(
            status_code=409,
            content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
        )

    @application.exception_handler(GateBlocked)
    async def gate_blocked_handler(request: Request, exc: GateBlocked):
        return JSONResponse(
            status_code=422,
            content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
        )

    @application.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError):
        return JSONResponse(
            status_code=500,
            content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
        )

    return application


app = create_app()
