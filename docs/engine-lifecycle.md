# Engine lifecycle

The chatbot is connect-only: it never starts, stops, pulls, or downloads a Model. Run lifecycle scripts from the repository root on the host.

## Operator preparation

Prepare each serving Engine and Model outside this repository. For WSL2 vLLM and SGLang on the RTX 5060 Ti, use Ubuntu with CUDA 12.8+ and a compatible PyTorch build, then manually install vLLM (>=0.17.0) and SGLang (0.5.x) in WSL. Copy the already-downloaded Qwen3.5-9B 4-bit Model into WSL and set `MODEL_PATH` to it.

The repository deliberately provides no installer. If a Model is absent, stop and have the operator download or copy it. The scripts fail before launching when a local Model path is missing; they never run package managers, `ollama pull`, `huggingface-cli`, or `snapshot_download`.

- Make each serving Engine executable available on `PATH` in its host or WSL environment.
- Put local Qwen3.5-9B 4-bit files in `models/`, or set `MODEL_PATH` to an existing path.
- Ollama requires `qwen3.5:9b` to have been installed separately; its startup script checks with `ollama list` and never runs a pull.

## Commands

From the repository root:

```bash
bash scripts/start-ollama.sh
bash scripts/start-llamacpp.sh
wsl bash scripts/start-vllm.sh
wsl bash scripts/start-sglang.sh
```

To start or stop all configured Engines, use `bash scripts/start-all.sh` or `bash scripts/stop-all.sh`. Windows hosts can use `scripts/start-all.ps1` and `scripts/stop-all.ps1`; the latter invokes vLLM and SGLang through WSL.

The scripts match `config.toml`: Ollama uses port 11434 and `qwen3.5:9b`; llama.cpp uses 8080 and `qwen3.5-9b`; vLLM uses 8000 and `qwen3.5-9b`; SGLang uses 30000 and `qwen3.5-9b`. WSL2 localhost forwarding makes ports 8000 and 30000 reachable from the host.

Each stop script targets only its matching Engine process. The app never invokes these scripts.
