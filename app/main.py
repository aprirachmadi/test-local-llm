from __future__ import annotations

import pathlib

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import load_config
from app.db import init_db

STATIC_DIR = pathlib.Path(__file__).resolve().parent / "static"


def create_app(config_path: pathlib.Path | str | None = None, db_path: pathlib.Path | str | None = None) -> FastAPI:
    cfg = load_config(config_path)
    init_db(db_path)

    app = FastAPI(title="test-local-llm")

    app.state.config = cfg

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    index = STATIC_DIR / "index.html"
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    def root():
        if index.exists():
            return FileResponse(str(index), media_type="text/html")
        return JSONResponse({"detail": "index.html not found"}, status_code=404)

    return app


app = create_app()
