# test-local-llm

A thin chatbot for exercising local Model-serving Engines through their OpenAI-compatible APIs. The app connects to running Engines; it never owns, downloads, starts, or stops a Model.

## Prerequisites

- Python 3.11 or newer.
- Poetry.
- Any configured Engine installed and available separately.
- For vLLM and SGLang: WSL2 Ubuntu with an NVIDIA driver visible through WSL, CUDA 12.8 or newer, and a CUDA-compatible PyTorch installation.
- The Qwen3.5-9B 4-bit Model already present locally. Ask the operator to download it separately; these scripts never download Models.

## Install and run the app

```bash
poetry install
poetry run uvicorn app.main:app --host 127.0.0.1 --port 8765
```

Open <http://127.0.0.1:8765>.

## Configure Engines

Edit `config.toml` to add or disable an Engine. Each Engine stanza supplies its display name, OpenAI-compatible `/v1` URL, Model name, and enabled flag. Adding another Engine requires only another stanza; the app has no Engine-specific adapter code, as decided in [ADR-0001](docs/adr/0001-openai-compatible-engine-seam.md).

The default ports and Model names are:

| Engine | URL | Model |
| --- | --- | --- |
| Ollama | `http://127.0.0.1:11434/v1` | `qwen3.5:9b` |
| vLLM | `http://127.0.0.1:8000/v1` | `qwen3.5-9b` |
| SGLang | `http://127.0.0.1:30000/v1` | `qwen3.5-9b` |
| llama.cpp | `http://127.0.0.1:8080/v1` | `qwen3.5-9b` |

## WSL vLLM and SGLang

These commands are preparation steps for an operator and are not run by this repository. Run them inside WSL2 Ubuntu after installing the NVIDIA/WSL prerequisites. Choose the PyTorch command matching the currently supported CUDA 12.8+ wheel, then install vLLM and SGLang versions compatible with that environment.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
# Install a CUDA 12.8+ PyTorch wheel appropriate for this host.
# Install vLLM >= 0.17.0 and SGLang 0.5.x compatible with that PyTorch wheel.
```

Copy or otherwise make the already-downloaded Qwen3.5-9B 4-bit Model available inside WSL. Run the following commands **inside the WSL2 Ubuntu shell**, using a Linux path visible to WSL:

```bash
export MODEL_PATH=/path/to/Qwen3.5-9B-Instruct-4bit
bash /mnt/path/to/test-local-llm/scripts/start-vllm.sh
bash /mnt/path/to/test-local-llm/scripts/start-sglang.sh
```

From a Windows host, invoke each script through WSL and pass a WSL path explicitly:

```powershell
wsl bash /mnt/path/to/test-local-llm/scripts/start-vllm.sh
wsl bash /mnt/path/to/test-local-llm/scripts/start-sglang.sh
```

Set `MODEL_PATH` inside WSL before these commands, or configure it in the WSL environment. A Windows path such as `C:\\models\\...` is not a valid `MODEL_PATH` for the Linux Engine process.

The scripts bind vLLM to port `8000` and SGLang to port `30000`. WSL2 localhost forwarding makes those ports reachable from the host at the URLs in `config.toml`. If forwarding is unavailable, configure the Engine URL to the WSL address without changing application code.

## Engine lifecycle

From the repository root:

```bash
bash scripts/start-all.sh
bash scripts/stop-all.sh
```

On Windows, use `scripts/start-all.ps1` and `scripts/stop-all.ps1`. The PowerShell aggregate script invokes vLLM and SGLang through WSL. Individual scripts are also available in `scripts/`.

Every local-file Engine script fails when its Model path is absent. No lifecycle script runs `ollama pull`, `huggingface-cli`, `snapshot_download`, or package installation. See [docs/engine-lifecycle.md](docs/engine-lifecycle.md) for the complete lifecycle contract.

## Smoke test flow

1. Start only the Engines whose Models and serving dependencies are already prepared.
2. Open the app and confirm the Engine inventory shows the expected health status.
3. Run an individual Engine's Smoke test to verify a streamed answer.
4. Run **Test all** to check all enabled Engines.
5. Create one Conversation per Engine and send the same prompt to each.

The automated test suite uses mocked HTTP transports and never starts an Engine or downloads a Model:

```bash
poetry run pytest
```
