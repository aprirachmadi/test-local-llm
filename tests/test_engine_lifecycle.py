from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "scripts"


def _read(name: str) -> str:
    return (SCRIPTS / name).read_text(encoding="utf-8")


def test_start_scripts_exist_and_match_configured_ports_and_models():
    expected = {
        "start-ollama.sh": ("11434", "qwen3.5:4b"),
        "start-llamacpp.sh": ("8080", "qwen3.5-4b"),
        "start-vllm.sh": ("8000", "qwen3.5-4b"),
        "start-sglang.sh": ("30000", "qwen3.5-4b"),
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


def test_native_start_scripts_require_preinstalled_models_and_use_repo_paths():
    ollama_sh = _read("start-ollama.sh")
    ollama_ps1 = _read("start-ollama.ps1")
    llamacpp_sh = _read("start-llamacpp.sh")
    llamacpp_ps1 = _read("start-llamacpp.ps1")

    assert "ollama list" in ollama_sh
    assert "ollama list" in ollama_ps1
    assert "OLLAMA_HOST=127.0.0.1:11434" in ollama_sh
    assert "OLLAMA_HOST = '127.0.0.1:11434'" in ollama_ps1
    assert "ollama serve" in ollama_sh
    assert "serve" in ollama_ps1
    assert "ROOT_DIR" in llamacpp_sh
    assert "Set-Location" in llamacpp_ps1
    assert "MODEL_PATH" in llamacpp_sh
    assert "MODEL_PATH" in llamacpp_ps1
    assert "this script never downloads models" in llamacpp_sh
    assert "this script never downloads models" in llamacpp_ps1


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
            EngineConfig(key=key, name=key, base_url="http://127.0.0.1:1234/v1", model="qwen3.5-4b", enabled=True)
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
    assert "or downloads a Model" in docs
    assert "vLLM (>=0.17.0)" in docs
    assert "SGLang (0.5.x)" in docs
    assert "localhost forwarding" in docs


def test_readme_documents_install_smoke_flow_and_download_boundary():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for required in (
        "poetry install",
        "scripts/start-all.sh",
        "Smoke test flow",
        "WSL2 Ubuntu",
        "CUDA 12.8",
        "Test all",
        "never download Models",
    ):
        assert required in readme


def test_wsl_start_scripts_use_configured_ports_and_local_model_paths():
    vllm = _read("start-vllm.sh")
    sglang = _read("start-sglang.sh")

    assert 'MODEL_PATH="${MODEL_PATH:-' in vllm
    assert 'MODEL_PATH="${MODEL_PATH:-' in sglang
    assert '"$VLLM" serve "$MODEL_PATH"' in vllm
    assert '"${SGLANG[@]}" --model-path "$MODEL_PATH"' in sglang
    assert "--host 127.0.0.1 --port 8000" in vllm
    assert "--host 127.0.0.1 --port 30000" in sglang
    assert "--served-model-name qwen3.5-4b" in vllm
    assert "--served-model-name qwen3.5-4b" in sglang
