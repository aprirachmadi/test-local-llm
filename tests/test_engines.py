from __future__ import annotations

import httpx
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
