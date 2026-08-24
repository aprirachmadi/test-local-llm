from __future__ import annotations

import datetime
import json

import httpx
import pathlib
import sqlite3
import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.config import load_config
from app.db import init_db
from app.engines import inventory, smoke_test_stream

STATIC_DIR = pathlib.Path(__file__).resolve().parent / "static"


class ConversationCreate(BaseModel):
    engine_key: str
    system_prompt: str = Field(default="", max_length=10000)
    think: bool = False
    title: str = Field(default="New Conversation", min_length=1, max_length=200)


class ConversationUpdate(BaseModel):
    system_prompt: str | None = Field(default=None, max_length=10000)
    think: bool | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=100000)


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

    @app.patch("/api/conversations/{conversation_id}")
    def update_conversation(conversation_id: str, payload: ConversationUpdate):
        changes = payload.model_dump(exclude_unset=True)
        if not changes:
            raise HTTPException(status_code=400, detail="No conversation changes supplied")
        with sqlite3.connect(app.state.db_path) as con:
            con.row_factory = sqlite3.Row
            row = con.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Conversation not found")
            values = {key: row[key] for key in ("title", "system_prompt", "think")}
            values.update(changes)
            now = datetime.datetime.now(datetime.UTC).isoformat()
            con.execute(
                "UPDATE conversations SET title = ?, system_prompt = ?, think = ?, updated_at = ? WHERE id = ?",
                (values["title"], values["system_prompt"], values["think"], now, conversation_id),
            )
            updated = con.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,)).fetchone()
        return read_conversation(updated)

    @app.get("/api/conversations/{conversation_id}/messages")
    def list_messages(conversation_id: str):
        with sqlite3.connect(app.state.db_path) as con:
            con.row_factory = sqlite3.Row
            if con.execute("SELECT 1 FROM conversations WHERE id = ?", (conversation_id,)).fetchone() is None:
                raise HTTPException(status_code=404, detail="Conversation not found")
            rows = con.execute(
                "SELECT id, role, content, created_at FROM messages WHERE conversation_id = ? ORDER BY created_at, id",
                (conversation_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    @app.post("/api/conversations/{conversation_id}/messages")
    def create_message(conversation_id: str, payload: MessageCreate):
        with sqlite3.connect(app.state.db_path) as con:
            con.row_factory = sqlite3.Row
            conversation = con.execute(
                "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
            ).fetchone()
            if conversation is None:
                raise HTTPException(status_code=404, detail="Conversation not found")
            history = con.execute(
                "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY created_at, id",
                (conversation_id,),
            ).fetchall()

        messages = []
        if conversation["system_prompt"]:
            messages.append({"role": "system", "content": conversation["system_prompt"]})
        messages.extend({"role": row["role"], "content": row["content"]} for row in history)
        messages.append({"role": "user", "content": payload.content})
        request_body = {
            "model": conversation["model"],
            "messages": messages,
            "stream": True,
            "think": bool(conversation["think"]),
        }

        def stream():
            assistant_content = ""
            failed = False
            try:
                with httpx.Client(transport=engine_transport, timeout=30.0) as client:
                    with client.stream(
                        "POST",
                        f"{cfg.engines[conversation['engine_key']].base_url.rstrip('/')}/chat/completions",
                        json=request_body,
                    ) as response:
                        response.raise_for_status()
                        for line in response.iter_lines():
                            if not line.startswith("data:"):
                                continue
                            data = line[5:].strip()
                            if data == "[DONE]":
                                break
                            event = json.loads(data)
                            if "error" in event:
                                failed = True
                                yield f"event: error\ndata: {json.dumps(event['error'])}\n\n"
                                break
                            delta = event.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                assistant_content += content
                                yield f"data: {json.dumps({'content': content})}\n\n"
            except (httpx.HTTPError, json.JSONDecodeError) as exc:
                failed = True
                yield f"event: error\ndata: {json.dumps({'message': str(exc)})}\n\n"
            if failed:
                return
            user_created_at = datetime.datetime.now(datetime.UTC)
            assistant_created_at = datetime.datetime.now(datetime.UTC)
            now = assistant_created_at.isoformat()
            with sqlite3.connect(app.state.db_path) as con:
                con.execute(
                    "INSERT INTO messages (id, conversation_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), conversation_id, "user", payload.content, user_created_at.isoformat()),
                )
                con.execute(
                    "INSERT INTO messages (id, conversation_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), conversation_id, "assistant", assistant_content, assistant_created_at.isoformat()),
                )
                con.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conversation_id))
            yield "data: [DONE]\n\n"

        return StreamingResponse(stream(), media_type="text/event-stream")

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/engines")
    def engines():
        return inventory(cfg.engines, transport=engine_transport)

    def smoke_response(engine_key: str):
        engine = cfg.engines.get(engine_key)
        if engine is None:
            raise HTTPException(status_code=404, detail=f"Unknown Engine: {engine_key}")
        if not engine.enabled:
            raise HTTPException(status_code=400, detail=f"Engine '{engine_key}' is disabled")

        def stream():
            for result in smoke_test_stream(engine, cfg.app.smoke_prompt, transport=engine_transport):
                yield f"data: {json.dumps({'engine_key': engine_key, **result})}\\n\\n"

        return StreamingResponse(stream(), media_type="text/event-stream")

    @app.post("/api/engines/smoke-test")
    def smoke_test_all():
        enabled_engines = [engine for engine in cfg.engines.values() if engine.enabled]

        def stream():
            for engine in enabled_engines:
                for result in smoke_test_stream(engine, cfg.app.smoke_prompt, transport=engine_transport):
                    yield f"data: {json.dumps({'engine_key': engine.key, **result})}\\n\\n"

        return StreamingResponse(stream(), media_type="text/event-stream")

    @app.post("/api/engines/{engine_key}/smoke-test")
    def smoke_test(engine_key: str):
        return smoke_response(engine_key)

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
