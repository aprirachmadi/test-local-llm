from __future__ import annotations

from dataclasses import asdict, dataclass
from collections.abc import Iterator
import json

import httpx

from app.config import EngineConfig


@dataclass(frozen=True)
class EngineStatus:
    key: str
    name: str
    base_url: str
    model: str
    enabled: bool
    status: str
    start_command: str
    wsl_start_command: str

    def as_dict(self) -> dict[str, str | bool]:
        return asdict(self)


def _start_commands(engine: EngineConfig) -> tuple[str, str]:
    command = f"bash scripts/start-{engine.key}.sh"
    wsl_command = f"wsl bash scripts/start-{engine.key}.sh"
    return command, wsl_command


def smoke_test_stream(
    engine: EngineConfig,
    prompt: str,
    transport: httpx.BaseTransport | None = None,
) -> Iterator[dict[str, str | bool]]:
    request_body = {
        "model": engine.model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
    }
    try:
        with httpx.Client(transport=transport, timeout=30.0) as client:
            with client.stream(
                "POST",
                f"{engine.base_url.rstrip('/')}/chat/completions",
                json=request_body,
            ) as response:
                response.raise_for_status()
                received = False
                completed = False
                for line in response.iter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        completed = True
                        break
                    event = json.loads(data)
                    if "error" in event:
                        error = event["error"]
                        message = error.get("message", "Engine returned an error") if isinstance(error, dict) else str(error)
                        yield {"success": False, "error_type": "engine_error", "message": message}
                        return
                    delta = event.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        received = True
                        yield {"success": True, "content": content}
                if not completed:
                    yield {"success": False, "error_type": "truncated_stream", "message": "Engine stream ended before completion"}
                elif not received:
                    yield {"success": False, "error_type": "empty_stream", "message": "Engine returned no answer"}
    except httpx.TimeoutException as exc:
        yield {"success": False, "error_type": "timeout", "message": str(exc) or "Engine request timed out"}
    except httpx.HTTPStatusError as exc:
        yield {"success": False, "error_type": "http_error", "message": f"Engine returned HTTP {exc.response.status_code}"}
    except httpx.ConnectError as exc:
        yield {"success": False, "error_type": "connection_refused", "message": str(exc) or "Connection refused"}
    except (httpx.RequestError, json.JSONDecodeError, IndexError, KeyError, TypeError) as exc:
        yield {"success": False, "error_type": "stream_error", "message": str(exc)}


def inventory(config: dict[str, EngineConfig], transport: httpx.BaseTransport | None = None) -> list[dict[str, str | bool]]:
    results: list[dict[str, str | bool]] = []
    with httpx.Client(transport=transport, timeout=2.0) as client:
        for engine in config.values():
            start_command, wsl_start_command = _start_commands(engine)
            status = "disabled" if not engine.enabled else "down"
            if engine.enabled:
                try:
                    response = client.get(f"{engine.base_url.rstrip('/')}/models")
                    if response.is_success:
                        status = "up"
                except httpx.RequestError:
                    pass
            results.append(
                EngineStatus(
                    key=engine.key,
                    name=engine.name,
                    base_url=engine.base_url,
                    model=engine.model,
                    enabled=engine.enabled,
                    status=status,
                    start_command=start_command,
                    wsl_start_command=wsl_start_command,
                ).as_dict()
            )
    return results
