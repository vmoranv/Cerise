"""
API Gateway

FastAPI application for REST and WebSocket endpoints.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .admin import router as admin_router
from .lifespan import lifespan
from .router import router


def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        title="Cerise API",
        description="AI-driven Live2D Virtual Character API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    app.include_router(admin_router)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
