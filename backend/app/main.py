from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.core.db import engine
from app.models import Base


def create_app() -> FastAPI:
    app = FastAPI(title="PCOD Detection Backend", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        # Frontend calls typically don't need cookies/auth; avoid wildcard+credentials CORS issues.
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(router)

    @app.on_event("startup")
    def on_startup() -> None:
        # For dev: create tables automatically.
        Base.metadata.create_all(bind=engine)

    return app


app = create_app()

