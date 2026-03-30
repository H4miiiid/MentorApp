from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.logging_config import configure_logging
from .core.log_buffer import attach_ring_buffer_handler

configure_logging()
attach_ring_buffer_handler()

from . import __version__
from .api.routers import admin, assignments, auth, documents, submissions, users
from .bootstrap_admin import ensure_default_admin
from .grading.grading_model_service import ensure_grading_models_bootstrapped
from .core.config import settings
from .db.database import init_db
from .grading import GradingWorker, create_grading_pipeline
from .schemas import HealthResponse

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    ensure_default_admin()
    try:
        ensure_grading_models_bootstrapped()
    except Exception as e:
        logger.warning("Grading model catalog bootstrap failed: %s", e)
    stop = asyncio.Event()
    worker_task: asyncio.Task[None] | None = None
    if settings.grading_worker_enabled:
        try:
            pipeline = create_grading_pipeline(settings)
            worker = GradingWorker(pipeline, settings)
            worker_task = asyncio.create_task(worker.run_until_stopped(stop))
            logger.info("[grading-worker] asyncio task created (logs also from grading.worker)")
        except ValueError as e:
            logger.error("Grading pipeline misconfigured: %s", e)
    yield
    if worker_task is not None:
        stop.set()
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass


def create_app() -> FastAPI:
    app = FastAPI(
        title="MentorApp V2 API",
        description="FastAPI + SQLModel + SQLite backend. Use /api/auth/login to obtain a JWT, then Authorize with Bearer.",
        version=__version__,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", version=__version__)

    # Public: /api/auth/register, /api/auth/login — private: /api/auth/me
    app.include_router(auth.router, prefix="/api")
    app.include_router(users.router, prefix="/api")
    app.include_router(assignments.router, prefix="/api")
    app.include_router(submissions.router, prefix="/api")
    app.include_router(documents.router, prefix="/api")
    app.include_router(admin.router, prefix="/api")

    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run(
        "AppV2.backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
