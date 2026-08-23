from __future__ import annotations

import pathlib
import sqlite3
import textwrap

import httpx
import pytest
from fastapi.testclient import TestClient


def _valid_toml() -> str:
    return textwrap.dedent(
        """
        [app]
        host = "127.0.0.1"
        port = 8765
        smoke_prompt = "Reply with exactly one word: pong"

        [engines.ollama]
        name = "Ollama"
        base_url = "http://127.0.0.1:11434/v1"
        model = "qwen3.5:9b"
        enabled = true

        [engines.vllm]
        name = "vLLM"
        base_url = "http://127.0.0.1:8000/v1"
        model = "qwen3.5-9b"
        enabled = true

        [engines.sglang]
        name = "SGLang"
        base_url = "http://127.0.0.1:30000/v1"
        model = "qwen3.5-9b"
        enabled = true

        [engines.llamacpp]
        name = "llama.cpp"
        base_url = "http://127.0.0.1:8080/v1"
        model = "qwen3.5-9b"
        enabled = true
        """
    )


def _write_config(tmp_path: pathlib.Path, content: str) -> pathlib.Path:
    p = tmp_path / "config.toml"
    p.write_text(content, encoding="utf-8")
    return p


def test_health_endpoint_uses_temp_db_and_mocked_engine_http(tmp_path):
    config_path = _write_config(tmp_path, _valid_toml())
    db_path = tmp_path / "data" / "chatbot.db"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        return httpx.Response(200, json={"choices": [{"message": {"content": "pong"}}]})

    transport = httpx.MockTransport(handler)

    from app.main import create_app

    app = create_app(config_path=config_path, db_path=db_path)
    client = TestClient(app)

    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

    resp = client.get("/")
    assert resp.status_code == 200
    assert "test-local-llm" in resp.text

    assert db_path.exists()
    con = sqlite3.connect(str(db_path))
    try:
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "conversations" in tables
        assert "messages" in tables
    finally:
        con.close()

    _ = transport


def test_config_rejects_missing_file(tmp_path):
    from app.config import load_config

    with pytest.raises(RuntimeError, match="not found"):
        load_config(tmp_path / "does-not-exist.toml")


def test_config_rejects_invalid_engine_base_url_not_v1(tmp_path):
    bad = _valid_toml().replace("http://127.0.0.1:11434/v1", "http://127.0.0.1:11434")
    config_path = _write_config(tmp_path, bad)
    from app.config import load_config

    with pytest.raises(RuntimeError, match="must end in /v1"):
        load_config(config_path)


def test_config_rejects_missing_app_section(tmp_path):
    bad = textwrap.dedent(
        """
        [engines.ollama]
        name = "Ollama"
        base_url = "http://127.0.0.1:11434/v1"
        model = "qwen3.5:9b"
        enabled = true
        """
    )
    config_path = _write_config(tmp_path, bad)
    from app.config import load_config

    with pytest.raises(RuntimeError, match="Missing \\[app\\]"):
        load_config(config_path)


def test_db_auto_creates_conversations_and_messages_tables(tmp_path):
    from app.db import init_db

    db_path = tmp_path / "data" / "chatbot.db"
    assert not db_path.exists()
    init_db(db_path)
    assert db_path.exists()
    con = sqlite3.connect(str(db_path))
    try:
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "conversations" in tables
        assert "messages" in tables
    finally:
        con.close()


def test_create_app_uses_config_host_port_and_smoke_prompt(tmp_path):
    content = _valid_toml().replace('port = 8765', 'port = 8766')
    config_path = _write_config(tmp_path, content)
    db_path = tmp_path / "data" / "chatbot.db"
    from app.main import create_app

    app = create_app(config_path=config_path, db_path=db_path)
    assert app.state.config.app.port == 8766
    assert app.state.config.app.host == "127.0.0.1"
    assert app.state.config.app.smoke_prompt
    assert len(app.state.config.engines) == 4
    assert set(app.state.config.engines.keys()) == {"ollama", "vllm", "sglang", "llamacpp"}


def test_httpx_mock_transport_seam_smoke(tmp_path):
    config_path = _write_config(tmp_path, _valid_toml())
    db_path = tmp_path / "data2" / "chatbot.db"

    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(200, json={"data": []})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    resp = client.get("http://127.0.0.1:11434/v1/models")
    assert resp.status_code == 200
    assert calls == ["http://127.0.0.1:11434/v1/models"]

    from app.main import create_app
    from fastapi.testclient import TestClient

    app = create_app(config_path=config_path, db_path=db_path)
    c = TestClient(app)
    assert c.get("/api/health").status_code == 200
