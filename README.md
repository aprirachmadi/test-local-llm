# test-local-llm

A thin chatbot for exercising local Model-serving Engines through their OpenAI-compatible APIs. The app connects to running Engines; it never owns, downloads, starts, or stops a Model.

Everything in this README assumes you start from a clean machine. Each Engine and its Model must be prepared by you (the operator) before the app or any script can use it. **Nothing here downloads a Model automatically** — any Model download is an explicit step you run yourself.

## Supported Engines

| Engine | Default URL (`/v1`) | Port | Default Model name |
| --- | --- | --- | --- |
| Ollama | `http://127.0.0.1:11434/v1` | 11434 | `qwen3.5:4b` |
| llama.cpp | `http://127.0.0.1:8080/v1` | 8080 | `qwen3.5-4b` |
| vLLM | `http://127.0.0.1:8000/v1` | 8000 | `qwen3.5-4b` |
| SGLang | `http://127.0.0.1:30000/v1` | 30000 | `qwen3.5-4b` |

These URLs and Model names come from `config.toml` and are matched by the lifecycle scripts. Add or disable an Engine by editing `config.toml` — each stanza only needs a display name, URL, Model name, and `enabled` flag. The app has no per-Engine adapter code ([ADR-0001](docs/adr/0001-openai-compatible-engine-seam.md)).

## Model types each Engine needs

The four Engines serve the same model but in different forms:

- **Ollama** needs the model *installed as an Ollama tag* (`qwen3.5:4b`).
- **llama.cpp** needs a single **GGUF file**: `models/Qwen3.5-4B-Instruct-Q4_K_M.gguf`.
- **vLLM** and **SGLang** need the **model directory** (Transformers weights): `models/Qwen3.5-4B`.

The startup scripts refuse to launch if the required Model is missing, and they never download Models. You download and place the Model yourself.

## Prerequisites (app)

- Python 3.11 or newer.
- Poetry.
- The Engine(s) you want to use, installed separately (see below).
- The Model(s) already present locally (see [Download the Model](#download-the-model)).

## Install and run the app

```bash
poetry install
poetry run uvicorn app.main:app --host 127.0.0.1 --port 8765
```

Open <http://127.0.0.1:8765>.

## Prepare the Engines

Pick the Engines you want. You do not need all four; only the ones you install and prepare will work.

### Ollama

Ollama installs with an official one-liner on either platform:

**Windows (PowerShell):**
```powershell
winget install Ollama.Ollama
```
Or download the installer from <https://ollama.com/download/windows>.

**Linux / WSL (bash):**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Make sure the `ollama` command is on your `PATH` afterward.

Download the model into Ollama. **This is the only command in this project's flow that downloads a Model, and you run it yourself:**

```bash
ollama pull qwen3.5:4b
```

Verify it is installed (the startup script checks exactly this):

```bash
ollama list
# expect a row beginning with  qwen3.5:4b
```

### llama.cpp

llama.cpp has no official one-liner installer; download the prebuilt `llama-server` binary from the [llama.cpp releases](https://github.com/ggml-org/llama.cpp/releases) (the `win-*` zip on Windows, a tar on Linux), unpack it, and put the executable on your `PATH`.

Place the GGUF file at:

```
models/Qwen3.5-4B-Instruct-Q4_K_M.gguf
```

Or point `MODEL_PATH` at an existing GGUF file.

### vLLM and SGLang (WSL2 required)

vLLM and SGLang run inside **WSL2 Ubuntu** — a real Linux environment on your Windows machine. Unlike the other Engines, you cannot run these from normal Windows PowerShell; the whole setup and launch happens *inside Ubuntu*. (If you already run Docker Desktop on Windows, that works through WSL, so you may already have it. To check: run `wsl --status`; you need a default distribution and version 2.)

**First, enter WSL.** Open a normal PowerShell window and type:

```powershell
wsl
```

Your prompt changes (e.g. to `you@host:~/path$`) — that means you're now inside Ubuntu. Type `exit` (or close the window) to get back to PowerShell. Throughout this section, you are inside Ubuntu, so the commands are `/bin/bash`, not PowerShell.

**CUDA and PyTorch — what "install CUDA 12.8" actually means here.** You do **not** install a separate NVIDIA CUDA Toolkit for this project. PyTorch and the vLLM/SGLang wheels each ship their own bundled CUDA runtime libraries, so the "CUDA version" is chosen by *which wheel you install*, and those libraries live inside the Poetry venv — no system-wide CUDA install, and nothing on your machine is replaced or conflicts with anything else.

**Which CUDA wheel should you use?** Your NVIDIA driver advertises a CUDA version via `nvidia-smi`. A driver reports the *highest* CUDA it supports, and a CUDA-capable driver runs **older** CUDA wheels fine (backward compatible). This project targets CUDA 12.8, so install the **CUDA 12.8** PyTorch / vLLM / SGLang wheels even if your driver reports CUDA 13 (e.g. driver 591.74 reports 13.1). Only if you specifically need CUDA 13 should you use the CUDA 13 wheels — but do not mix major CUDA versions across PyTorch, vLLM, and SGLang.

Now, still **inside Ubuntu**, set up a Poetry-managed Engine environment in a directory of your choice (the README's Windows `D:\` drive is visible in WSL under `/mnt/d`; pick a plain Linux folder such as `~/engines` for best speed, but you may use `/mnt/d/...`). Run these in order — register the CUDA 12.8 PyTorch index first, then add `torch`, then vLLM and SGLang:

```bash
# From a directory you will run the engines from, inside WSL.
poetry init -n
# Register the CUDA 12.8 PyTorch package index so the torch line below can use it.
poetry source add --priority=explicit pytorch-cu128 https://download.pytorch.org/whl/cu128
# Install the CUDA 12.8 PyTorch wheel from that index (this is the "CUDA install" step).
poetry add torch --source pytorch-cu128
poetry add "vllm>=0.17.0"
poetry add --allow-prereleases "sglang>=0.5,<0.6"     # --allow-prereleases matches pip's --prerelease=allow
poetry run vllm --version
poetry run python -m sglang.launch_server --help
```

The `poetry source add ... pytorch-cu128` line must come **before** `poetry add torch --source pytorch-cu128`, or the latter fails because the source does not exist yet. vLLM and SGLang wheels should also be built for the same CUDA major version; add them per their docs ([SGLang](https://docs.sglang.ai/get_started/install.html), [vLLM](https://docs.vllm.ai/en/latest/getting_started/installation.html)) and keep PyTorch/vLLM/SGLang on one CUDA major version.

If `poetry` is not found when you run `poetry init`, you are not inside WSL yet (run `wsl` first), or Poetry is not installed inside Ubuntu — install it there with `pipx install poetry` or `pip install --user poetry`. Note: the app's Poetry on Windows is a *separate* install from the one you need here; installing it in Ubuntu does not affect the app.

**Before continuing, confirm the NVIDIA driver is visible inside WSL:** run `nvidia-smi` and check it lists your GPU (e.g. `GeForce RTX 5060 Ti`). It also reports a CUDA version — this comes from your Windows NVIDIA driver, not from any installed software, and it does not force you onto that CUDA version (see "CUDA and PyTorch" above).

`poetry add "vllm>=0.17.0"` and `poetry add --allow-prereleases "sglang>=0.5,<0.6"` are the one-line installs for this project's supported versions. For SGLang, `--allow-prereleases` is required because some of its dependencies are pre-releases. Follow the CUDA-specific install steps for the variant you chose (CUDA 12.8 recommended) in the [SGLang installation docs](https://docs.sglang.ai/get_started/install.html) and the [vLLM installation docs](https://docs.vllm.ai/en/latest/getting_started/installation.html).

Make the already-downloaded Model directory visible inside WSL, for example by placing it at a path WSL can reach (via `/mnt/c/...` or inside the WSL filesystem). Set `MODEL_PATH` to that **Linux** path inside WSL before starting:

```bash
export MODEL_PATH=/path/to/Qwen3.5-4B
```

A Windows path such as `C:\models\...` is **not** a valid `MODEL_PATH` for a Linux Engine process. If your Model is already at `models/Qwen3.5-4B` under the repo, the scripts find it relative to the repo root so `MODEL_PATH` is optional.

## Download the Model

The project uses **`Qwen/Qwen3.5-4B`** on [Hugging Face](https://huggingface.co/Qwen/Qwen3.5-4B) (also mirrored on [ModelScope](https://www.modelscope.cn/models/qwen/Qwen3.5-4B/summary), useful if Hugging Face is slow or blocked). It is an Apache-2.0 multimodal model (image/video + text), and its ~9.3 GB BF16 weights fit comfortably in a 16 GB NVIDIA GPU. Downloading is a manual step you run yourself — none of it is automated here:

- **Ollama**: `ollama pull qwen3.5:4b` (Ollama fetches the tag for you).
- **llama.cpp**: download a **GGUF** quantization of the model as `Qwen3.5-4B-Instruct-Q4_K_M.gguf` into `models/`. GGUF files are community-created quantizations — Qwen does not publish a GGUF on the official repo, so confirm you download it from an authoritative quantizer's repo (search Hugging Face for `qwen3.5 4b Q4_K_M gguf`).
- **vLLM / SGLang**: download the **official `Qwen/Qwen3.5-4B` model directory** into `models/` (as `Qwen3.5-4B`) or a WSL-visible path. This is the repo the start scripts' `MODEL_PATH` points at by default. vLLM/SGLang serve a directory of weights, so the folder must contain the model files (`config.json`, `*.safetensors`, tokenizer files), not a single GGUF.

The scripts check that these exact paths exist and fail early if you've placed the model under a different name or path — set `MODEL_PATH` (or move the files) if your model lives elsewhere.

## Start the Engines

Run the lifecycle scripts from the repository root. Which set you use depends on your platform.

**PATH requirement:** the startup scripts launch engines by bare name (`ollama`, `llama-server`, `vllm`, `python -m sglang.launch_server`). Make sure each Engine's executable is on the `PATH` of the shell that runs the script. For vLLM/SGLang installed via Poetry inside WSL, run from the activated Poetry venv (e.g. `poetry shell`, or `poetry run ...`), and for the PowerShell `start-all.ps1` the WSL commands are non-interactive, so export the Poetry bin directory into `PATH` in your WSL `~/.bashrc` or via an explicit `PATH=... wsl bash ...`.

### Linux / WSL (bash)

Start one Engine:

```bash
bash scripts/start-ollama.sh      # native host
bash scripts/start-llamacpp.sh    # native host
wsl bash scripts/start-vllm.sh    # inside WSL
wsl bash scripts/start-sglang.sh  # inside WSL
```

Start all four:

```bash
bash scripts/start-all.sh
```

Each `.sh` script runs **in the foreground** (`exec`) — it keeps your terminal busy while the Engine serves, so run each in its own terminal. See the shell's expected behavior below.

### Windows host (PowerShell)

Start one Engine:

```powershell
.\scripts\start-ollama.ps1        # native host
.\scripts\start-llamacpp.ps1      # native host
```

Start all four (the aggregate script launches vLLM and SGLang through WSL for you):

```powershell
.\scripts\start-all.ps1
```

Each `.ps1` script starts the Engine as a child process and then blocks waiting for it, so keep it in its own PowerShell window.

### What the scripts check before starting

Every startup script fails early rather than download anything:

- **Ollama**: aborts if `qwen3.5:4b` is not in `ollama list`.
- **llama.cpp / vLLM / SGLang**: abort if the `MODEL_PATH` (or default `models/` location) does not exist.

No lifecycle script runs `ollama pull`, `huggingface-cli`, `snapshot_download`, or package installation. See [docs/engine-lifecycle.md](docs/engine-lifecycle.md) for the full contract.

## Stop the Engines

From the repository root:

```bash
bash scripts/stop-all.sh                      # Linux / WSL
.\scripts\stop-all.ps1                        # Windows host
```

For one Engine at a time, use the matching `stop-*` script, e.g. `bash scripts/stop-vllm.sh`. Each stop script targets only its own Engine process. The app never starts or stops Engines for you.

## Smoke test flow

1. Start only the Engines whose Models and serving dependencies are already prepared.
2. Open the app and confirm the Engine inventory shows the expected health status.
3. Run an individual Engine's Smoke test to verify a streamed answer.
4. Run **Test all** to check all enabled Engines.
5. Create one Conversation per Engine and send the same prompt to each.

## Tests

The automated test suite uses mocked HTTP transports and never starts an Engine or downloads a Model:

```bash
poetry run pytest
```