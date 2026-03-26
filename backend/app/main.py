from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.core.db import engine
from app.models import Base


def _ensure_sqlite_column(database_path: str, table: str, column: str, ddl: str) -> None:
    """
    Tiny dev-friendly migration for SQLite. Adds a column if missing.
    This keeps existing app.db working when we introduce new fields.
    """
    import sqlite3

    con = sqlite3.connect(database_path)
    try:
        cur = con.cursor()
        cols = [r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()]
        if column not in cols:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")
            con.commit()
    finally:
        con.close()


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

        # Lightweight SQLite migration(s)
        # Note: settings.database_url is sqlite:///./app.db, and uvicorn is started from backend/
        if settings.database_url.startswith("sqlite"):
            # Only run if the table exists (PRAGMA table_info returns empty list otherwise).
            _ensure_sqlite_column("./app.db", "assessments", "cramps_severity", "cramps_severity TEXT NOT NULL DEFAULT ''")

    return app


app = create_app()

