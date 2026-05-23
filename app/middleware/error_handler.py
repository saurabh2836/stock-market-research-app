"""
app/middleware/error_handler.py
--------------------------------
Maps common exceptions to structured JSON error responses.
"""
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("api.errors")


def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        logger.warning("ValueError on %s: %s", request.url.path, exc)
        return JSONResponse(status_code=400, content={"error": "Bad request", "detail": str(exc)})

    @app.exception_handler(FileNotFoundError)
    async def file_not_found_handler(request: Request, exc: FileNotFoundError) -> JSONResponse:
        logger.warning("FileNotFoundError on %s: %s", request.url.path, exc)
        return JSONResponse(status_code=404, content={"error": "Not found", "detail": str(exc)})

    @app.exception_handler(Exception)
    async def generic_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s", request.url.path)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(exc)},
        )
