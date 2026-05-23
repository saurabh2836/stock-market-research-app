"""
app/core/app_factory.py
-----------------------
Creates and configures the FastAPI application.
Registers routers and middleware in one place.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.middleware.logging_middleware import LoggingMiddleware
from app.middleware.error_handler import register_exception_handlers
from app.api.routes import ingest, query, ask, plot


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_title,
        version=settings.app_version,
        debug=settings.debug,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── Middleware ────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(LoggingMiddleware)

    # ── Exception handlers ────────────────────────────
    register_exception_handlers(app)

    # ── Routers ───────────────────────────────────────
    app.include_router(ingest.router, prefix="/ingest", tags=["Ingest"])
    app.include_router(query.router,  prefix="/query",  tags=["Query"])
    app.include_router(ask.router,    prefix="/ask",    tags=["Ask"])
    app.include_router(plot.router,   prefix="/plot",   tags=["Plot"])

    @app.get("/health", tags=["Health"])
    async def health():
        return {"status": "ok", "version": settings.app_version}

    return app
