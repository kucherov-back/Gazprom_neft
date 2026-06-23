"""Точка входа приложения."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.db.engine import init_db
from app.logging_config import configure_logging
from app.routers.upload import router as upload_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("Application started")
    yield


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="Document processing - backend", version="0.1.0", lifespan=lifespan)
    app.include_router(upload_router)

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
        logger.warning("Integrity error on %s: %s", request.url.path, exc)
        return JSONResponse(status_code=409, content={"detail": "Resource conflict"})

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s", request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
