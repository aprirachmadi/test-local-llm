from __future__ import annotations

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import EngineConfig
from app.engines import inventory
from app.main import create_app


def _engines() -> dict[str, EngineConfig]:
    return {
        "up": EngineConfig("up", "Up", "http://up.test/v1", "model-up", True),
        "down": EngineConfig("down", "Down", "http://down.test/v1", "model-down", True),
        "timeout": EngineConfig("timeout", "Timeout", "http://timeout.test/v1", "model-timeout", True),
        "disabled": EngineConfig("disabled", "Disabled", "http://disabled.test/v1", "model-disabled", False),
    }


def test_inventory_reports_up_down_timeout_and_disabled_without_polling_disabled():
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.host or "")
        if request.url.host == "up.test":
            return httpx.Response(200, json={"data": []})
        if request.url.host == "timeout.test":
            raise httpx.ReadTimeout("probe timed out")
        return httpx.Response(503)

    result = inventory(_engines(), transport=httpx.MockTransport(handler))

    assert {item["key"]: item["status"] for item in result} == {
        "up": "up",
        "down": "down",
        "timeout": "down",
        "disabled": "disabled",
    }
    assert calls == ["up.test", "down.test", "timeout.test"]
    assert result[1]["start_command"] == "bash scripts/start-down.sh"
    assert result[1]["wsl_start_command"] == "wsl bash scripts/start-down.sh"


def test_engines_endpoint_uses_injected_mock_transport(tmp_path):
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.host or "")
        return httpx.Response(200, json={"data": []})

    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
        [app]
        host = "127.0.0.1"
        port = 8765

        [engines.test]
        name = "Test"
        base_url = "http://test.test:1234/v1"
        model = "test-model"
        enabled = true
        """,
        encoding="utf-8",
    )
    app = create_app(config_path=config_path, db_path=tmp_path / "chatbot.db", engine_transport=httpx.MockTransport(handler))

    response = TestClient(app).get("/api/engines")

    assert response.status_code == 200
    assert response.json()[0]["status"] == "up"
    assert calls == ["test.test"]


def _smoke_config(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
        [app]
        host = "127.0.0.1"
        port = 8765
        smoke_prompt = "Reply with exactly one word: pong"

        [engines.test]
        name = "Test"
        base_url = "http://test.test:1234/v1"
        model = "test-model"
        enabled = true

        [engines.disabled]
        name = "Disabled"
        base_url = "http://disabled.test:1234/v1"
        model = "disabled-model"
        enabled = false
        """,
        encoding="utf-8",
    )
    return config_path


def test_smoke_test_streams_success_and_sends_prompt(tmp_path):
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=b'data: {"choices":[{"delta":{"content":"pong"}}]}\n\ndata: [DONE]\n\n',
        )

    app = create_app(
        config_path=_smoke_config(tmp_path),
        db_path=tmp_path / "chatbot.db",
        engine_transport=httpx.MockTransport(handler),
    )
    response = TestClient(app).post("/api/engines/test/smoke-test")

    assert response.status_code == 200
    events = [json.loads(event.removeprefix("data: ")) for event in response.text.strip().split("\n\n")]
    assert events == [
        {"engine_key": "test", "success": True, "content": "pong"},
    ]
    assert response.text.endswith("\n\n")
    assert requests[0].url.path == "/v1/chat/completions"
    assert json.loads(requests[0].content) == {
        "model": "test-model",
        "messages": [{"role": "user", "content": "Reply with exactly one word: pong"}],
        "stream": True,
    }


@pytest.mark.parametrize(
    ("failure", "expected_type"),
    [
        ("http", "http_error"),
        ("timeout", "timeout"),
        ("connection", "connection_refused"),
        ("truncated", "truncated_stream"),
    ],
)
def test_smoke_test_reports_failure_modes(tmp_path, failure, expected_type):
    def handler(request: httpx.Request) -> httpx.Response:
        if failure == "http":
            return httpx.Response(503)
        if failure == "timeout":
            raise httpx.ReadTimeout("timed out")
        if failure == "connection":
            raise httpx.ConnectError("refused")
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=b'data: {"choices":[{"delta":{"content":"partial"}}]}\n\n',
        )

    app = create_app(
        config_path=_smoke_config(tmp_path),
        db_path=tmp_path / "chatbot.db",
        engine_transport=httpx.MockTransport(handler),
    )
    response = TestClient(app).post("/api/engines/test/smoke-test")

    assert response.status_code == 200
    assert f'"error_type": "{expected_type}"' in response.text
    assert '"success": false' in response.text


def test_smoke_test_all_skips_disabled_engines(tmp_path):
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.host or "")
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=b'data: {"choices":[{"delta":{"content":"pong"}}]}\n\ndata: [DONE]\n\n',
        )

    app = create_app(
        config_path=_smoke_config(tmp_path),
        db_path=tmp_path / "chatbot.db",
        engine_transport=httpx.MockTransport(handler),
    )
    response = TestClient(app).post("/api/engines/smoke-test")

    assert response.status_code == 200
    assert '"engine_key": "test"' in response.text
    assert "disabled" not in response.text
    assert calls == ["test.test"]


def test_smoke_test_rejects_unknown_and_disabled_engines(tmp_path):
    app = create_app(
        config_path=_smoke_config(tmp_path), db_path=tmp_path / "chatbot.db"
    )
    client = TestClient(app)

    assert client.post("/api/engines/missing/smoke-test").status_code == 404
    assert client.post("/api/engines/disabled/smoke-test").status_code == 400
