from __future__ import annotations

import datetime

import httpx
import pathlib
import sqlite3
import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import load_config
from app.db import init_db
from app.engines import inventory

STATIC_DIR = pathlib.Path(__file__).resolve().parent / "static"


class ConversationCreate(BaseModel):
    engine_key: str
    system_prompt: str = Field(default="", max_length=10000)
    think: bool = False
    title: str = Field(default="New Conversation", min_length=1, max_length=200)


def create_app(
    config_path: pathlib.Path | str | None = None,
    db_path: pathlib.Path | str | None = None,
    engine_transport: httpx.BaseTransport | None = None,
) -> FastAPI:
    cfg = load_config(config_path)
    init_db(db_path)

    app = FastAPI(title="test-local-llm")

    app.state.config = cfg
    app.state.db_path = pathlib.Path(db_path) if db_path is not None else pathlib.Path(__file__).resolve().parents[1] / "data" / "chatbot.db"

    def read_conversation(row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "title": row["title"],
            "engine_key": row["engine_key"],
            "model": row["model"],
            "system_prompt": row["system_prompt"],
            "think": bool(row["think"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    @app.post("/api/conversations", status_code=201)
    def create_conversation(payload: ConversationCreate):
        engine = cfg.engines.get(payload.engine_key)
        if engine is None:
            raise HTTPException(status_code=400, detail=f"Unknown Engine: {payload.engine_key}")
        if not engine.enabled:
            raise HTTPException(status_code=400, detail=f"Engine '{payload.engine_key}' is disabled")
        now = datetime.datetime.now(datetime.UTC).isoformat()
        conversation_id = str(uuid.uuid4())
        with sqlite3.connect(app.state.db_path) as con:
            con.execute(
                "INSERT INTO conversations (id, title, engine_key, model, system_prompt, think, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (conversation_id, payload.title, payload.engine_key, engine.model, payload.system_prompt, payload.think, now, now),
            )
            con.row_factory = sqlite3.Row
            row = con.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
        return read_conversation(row)

    @app.get("/api/conversations")
    def list_conversations():
        with sqlite3.connect(app.state.db_path) as con:
            con.row_factory = sqlite3.Row
            rows = con.execute("SELECT * FROM conversations ORDER BY created_at DESC, id DESC").fetchall()
        return [read_conversation(row) for row in rows]

    @app.get("/api/conversations/{conversation_id}")
    def get_conversation(conversation_id: str):
        with sqlite3.connect(app.state.db_path) as con:
            con.row_factory = sqlite3.Row
            row = con.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return read_conversation(row)

    @app.delete("/api/conversations/{conversation_id}", status_code=204)
    def delete_conversation(conversation_id: str):
        with sqlite3.connect(app.state.db_path) as con:
            result = con.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Conversation not found")

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/engines")
    def engines():
        return inventory(cfg.engines, transport=engine_transport)

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
