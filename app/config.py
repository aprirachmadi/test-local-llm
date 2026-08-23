from __future__ import annotations

import pathlib
import tomllib
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    host: str
    port: int
    smoke_prompt: str


@dataclass(frozen=True)
class EngineConfig:
    key: str
    name: str
    base_url: str
    model: str
    enabled: bool


@dataclass(frozen=True)
class Config:
    app: AppConfig
    engines: dict[str, EngineConfig]


def _repo_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[1]


def _default_config_path() -> pathlib.Path:
    return _repo_root() / "config.toml"


def load_config(path: pathlib.Path | str | None = None) -> Config:
    p = pathlib.Path(path) if path is not None else _default_config_path()
    if not p.exists():
        raise RuntimeError(f"config.toml not found at {p} — create it from config.toml at repo root")
    try:
        data = tomllib.load(open(p, "rb"))
    except Exception as e:
        raise RuntimeError(f"Invalid config.toml at {p}: {e}") from e

    if "app" not in data or not isinstance(data["app"], dict):
        raise RuntimeError("Missing [app] section in config.toml")

    app_raw = data["app"]
    host = app_raw.get("host")
    port = app_raw.get("port")
    smoke_prompt = app_raw.get("smoke_prompt", "Reply with exactly one word: pong")

    if not isinstance(host, str) or not host.strip():
        raise RuntimeError("Missing/invalid [app].host in config.toml — expected non-empty string")
    if not isinstance(port, int) or not (1 <= port <= 65535):
        raise RuntimeError("Missing/invalid [app].port in config.toml — expected integer 1-65535")
    if not isinstance(smoke_prompt, str) or not smoke_prompt.strip():
        raise RuntimeError("Missing/invalid [app].smoke_prompt in config.toml — expected non-empty string")

    app_cfg = AppConfig(host=host, port=port, smoke_prompt=smoke_prompt)

    if "engines" not in data or not isinstance(data["engines"], dict) or not data["engines"]:
        raise RuntimeError("Missing [engines] section in config.toml — expected at least one engine")

    engines: dict[str, EngineConfig] = {}
    for key, raw in data["engines"].items():
        if not isinstance(raw, dict):
            raise RuntimeError(f"Engine '{key}' invalid in config.toml — expected table with name, base_url, model, enabled")
        name = raw.get("name")
        base_url = raw.get("base_url")
        model = raw.get("model")
        enabled = raw.get("enabled")
        if not isinstance(name, str) or not name.strip():
            raise RuntimeError(f"Engine '{key}' missing/invalid 'name' in config.toml")
        if not isinstance(base_url, str) or not base_url.strip():
            raise RuntimeError(f"Engine '{key}' missing/invalid 'base_url' in config.toml")
        if not base_url.startswith("http://") and not base_url.startswith("https://"):
            raise RuntimeError(f"Engine '{key}' base_url must start with http:// or https:// in config.toml")
        if not base_url.rstrip("/").endswith("/v1"):
            raise RuntimeError(f"Engine '{key}' base_url must end in /v1 in config.toml (got {base_url!r})")
        if not isinstance(model, str) or not model.strip():
            raise RuntimeError(f"Engine '{key}' missing/invalid 'model' in config.toml")
        if not isinstance(enabled, bool):
            raise RuntimeError(f"Engine '{key}' missing/invalid 'enabled' in config.toml — expected true/false")
        engines[key] = EngineConfig(key=key, name=name, base_url=base_url, model=model, enabled=enabled)

    return Config(app=app_cfg, engines=engines)
