from __future__ import annotations

from dataclasses import asdict, dataclass

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
    if engine.key in {"vllm", "sglang"}:
        command = wsl_command
    return command, wsl_command


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
