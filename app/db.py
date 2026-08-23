from __future__ import annotations

import pathlib
import sqlite3


def default_db_path() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[1] / "data" / "chatbot.db"


def init_db(db_path: pathlib.Path | str | None = None) -> pathlib.Path:
    p = pathlib.Path(db_path) if db_path is not None else default_db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(p))
    try:
        con.execute("PRAGMA foreign_keys = ON")
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                engine_key TEXT NOT NULL,
                model TEXT NOT NULL,
                system_prompt TEXT NOT NULL DEFAULT '',
                think INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        con.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id)")
        con.commit()
    finally:
        con.close()
    return p
