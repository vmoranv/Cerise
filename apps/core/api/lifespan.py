"""Application lifespan management."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .container import build_services, shutdown_services

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager."""
    logger.info("Starting Cerise API server...")
    app.state.services = await build_services()
    logger.info("Cerise API server started")

    yield

    logger.info("Shutting down Cerise API server...")
    services = getattr(app.state, "services", None)
    if services:
        await shutdown_services(services)
    logger.info("Cerise API server stopped")
