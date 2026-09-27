import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from medialab_web.auth import LoginRequired, check_startup_config
from medialab_web.client import OrchestratorClient
from medialab_web.config import AppConfig, config
from medialab_web.limiter import limiter
from medialab_web.rendering import STATIC_DIR, render
from medialab_web.routes import discover, jobs, pages, search, settings, shows, system, trailers

logger = logging.getLogger(__name__)


def create_app(cfg: AppConfig | None = None) -> FastAPI:
    cfg = cfg or config

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        check_startup_config(cfg)
        app.state.client = OrchestratorClient(
            base_url=cfg.orchestrator_url,
            api_key=cfg.orchestrator_api_key,
            torrent_search_timeout=cfg.gateway_timeout_seconds,
        )
        yield
        await app.state.client.close()

    app = FastAPI(title="medialab-web", docs_url=None, redoc_url=None, lifespan=lifespan)
    app.state.config = cfg
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)

    @app.exception_handler(LoginRequired)
    async def _redirect_to_login(request: Request, exc: LoginRequired) -> RedirectResponse:
        return RedirectResponse(exc.location, status_code=exc.status_code)

    @app.exception_handler(RateLimitExceeded)
    async def _too_many(request: Request, exc: RateLimitExceeded) -> Response:
        return render(
            request,
            "login.html",
            {"error": "Too many attempts; wait a minute."},
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    app.include_router(system.router)
    app.include_router(pages.router)
    app.include_router(jobs.router)
    app.include_router(search.router)
    app.include_router(settings.router)
    app.include_router(discover.router)
    app.include_router(shows.router)
    app.include_router(trailers.router)
    return app


app = create_app()


def main() -> None:
    logging.basicConfig(level=config.log_level)
    uvicorn.run("medialab_web.main:app", host=config.api_host, port=config.api_port)


def dev() -> None:
    logging.basicConfig(level=config.log_level)
    uvicorn.run("medialab_web.main:app", host=config.api_host, port=config.api_port, reload=True)
