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


def _check_sandbox_available() -> None:
    """Log a loud WARNING if the grading sandbox can't run — so operators notice
    *before* students lose submissions to ``sandbox_unavailable``.

    We intentionally do not raise: the API should still boot (admin pages, auth,
    assignment management) even when Docker is down. But the banner makes it
    obvious in logs that any submission will be rejected with an infra error.
    """
    from .workflow_runtime.sandbox import (
        docker_cli_available,
        sandbox_allow_unsafe_fallback,
        sandbox_docker_enabled,
        _docker_socket_exists,
    )

    cli_ok = docker_cli_available()
    socket_ok = _docker_socket_exists()
    docker_ok = sandbox_docker_enabled() and socket_ok
    fallback = sandbox_allow_unsafe_fallback()
    if docker_ok:
        logger.info(
            "[sandbox] Docker CLI + socket detected — student code will run in isolated containers."
        )
        return
    if fallback:
        logger.warning(
            "[sandbox] Docker unavailable (cli=%s socket=%s). Falling back to UNSAFE in-process execution "
            "(SANDBOX_ALLOW_UNSAFE_FALLBACK=true). Do not use in production.",
            cli_ok,
            socket_ok,
        )
        return
    logger.error(
        "[sandbox] UNUSABLE — every grading submission will fail with sandbox_unavailable. "
        "docker_cli=%s docker_socket=%s. Fix: (a) rebuild backend image so `docker` is on PATH "
        "(see AppV2/backend/Dockerfile), (b) mount /var/run/docker.sock in docker-compose.yml, "
        "or (c) set SANDBOX_ALLOW_UNSAFE_FALLBACK=true for local dev only.",
        cli_ok,
        socket_ok,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    ensure_default_admin()
    _check_sandbox_available()
    try:
        ensure_grading_models_bootstrapped()
    except Exception as e:
        logger.warning("Grading model catalog bootstrap failed: %s", e)

    async def _maybe_warmup_rag() -> None:
        from AppV2.backend.workflow_runtime.config import CFG

        if not CFG.rag_warmup_on_startup:
            return

        def _load() -> None:
            from AppV2.backend.workflow_runtime.rag import get_chroma_collection, get_reranker

            get_chroma_collection()
            get_reranker()

        try:
            await asyncio.to_thread(_load)
            logger.info("[rag] embedder + reranker warmup completed")
        except Exception as e:
            logger.warning("[rag] warmup skipped (non-fatal): %s", e)

    await _maybe_warmup_rag()

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
