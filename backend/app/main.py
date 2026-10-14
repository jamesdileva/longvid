"""FastAPI application factory and programmatic entrypoint.

Run from the ``backend/`` directory::

    .venv\\Scripts\\python -m app.main
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import api_router
from app.config import get_settings
from app.database import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("longvid")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Initialize storage on startup."""
    settings = get_settings()
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    init_db()
    logger.info("LongVid backend initialized (data dir: %s)", settings.data_dir)
    yield


def create_app() -> FastAPI:
    """Build the application, wire routers, and initialize the database."""
    app = FastAPI(title="LongVid", version=__version__, lifespan=lifespan)
    # The Vite dev server runs on a different origin than the backend.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "null",  # packaged renderer loads from file:// (Origin: null)
        ],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    return app


app = create_app()


def run() -> None:
    """Serve the API with uvicorn using configured host/port."""
    import uvicorn

    settings = get_settings()
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    init_db()
    uvicorn.run(app, host=settings.host, port=settings.port, log_level=settings.log_level)


if __name__ == "__main__":
    run()
