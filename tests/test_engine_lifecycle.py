from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "scripts"


def _read(name: str) -> str:
    return (SCRIPTS / name).read_text(encoding="utf-8")


def test_start_scripts_exist_and_match_configured_ports_and_models():
    expected = {
        "start-ollama.sh": ("11434", "qwen3.5:9b"),
        "start-llamacpp.sh": ("8080", "qwen3.5-9b"),
        "start-vllm.sh": ("8000", "qwen3.5-9b"),
        "start-sglang.sh": ("30000", "qwen3.5-9b"),
    }

    for name, (port, model) in expected.items():
        script = _read(name)
        assert f"--port {port}" in script or f":{port}" in script
        assert model in script


def test_matching_stop_and_aggregate_scripts_exist():
    for engine in ("ollama", "llamacpp", "vllm", "sglang"):
        assert (SCRIPTS / f"start-{engine}.sh").exists()
        assert (SCRIPTS / f"stop-{engine}.sh").exists()

    assert (SCRIPTS / "start-all.sh").exists()
    assert (SCRIPTS / "stop-all.sh").exists()
    assert (SCRIPTS / "start-all.ps1").exists()
    assert (SCRIPTS / "stop-all.ps1").exists()


def test_scripts_never_download_models():
    script_text = "\n".join(
        line for path in SCRIPTS.iterdir() for line in path.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("#")
    )
    for forbidden in ("ollama pull", "huggingface-cli", "snapshot_download", "pip install"):
        assert forbidden not in script_text


def test_stop_scripts_use_scoped_pid_files():
    for engine in ("ollama", "llamacpp", "vllm", "sglang"):
        script = _read(f"stop-{engine}.sh")
        assert "pkill" not in script
        assert f"{engine}.pid" in script


def test_engine_inventory_hints_match_start_script_invocations():
    from app.config import EngineConfig
    from app.engines import _start_commands

    for key in ("ollama", "vllm", "sglang", "llamacpp"):
        commands = _start_commands(
            EngineConfig(key=key, name=key, base_url="http://127.0.0.1:1234/v1", model="qwen3.5-9b", enabled=True)
        )
        assert f"scripts/start-{key}.sh" in commands[0]
        assert f"scripts/start-{key}.sh" in commands[1]
        assert commands[0].startswith("bash ")
        assert commands[1].startswith("wsl ")


def test_lifecycle_docs_cover_wsl_gpu_prerequisites():
    docs = (ROOT / "docs" / "engine-lifecycle.md").read_text(encoding="utf-8")
    assert "WSL" in docs
    assert "CUDA 12.8+" in docs
    assert "RTX 5060 Ti" in docs
    assert "do not download models" in docs
