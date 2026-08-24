# Engine lifecycle

The chatbot is connect-only: it never starts, stops, pulls, or downloads a Model. Run lifecycle scripts from the repository root on the host.

## Prerequisites

- Install each serving Engine separately and make its executable available on `PATH`.
- Put the Qwen3.5-9B 4-bit files in `models/`, or set `MODEL_PATH` to an existing local model path before starting llama.cpp, vLLM, or SGLang.
- The scripts intentionally fail when the model path is absent. They do not download models.
- vLLM and SGLang scripts run in WSL. For an RTX 5060 Ti, use CUDA 12.8+ and a PyTorch build compatible with that CUDA version.
- Ollama requires the `qwen3.5:9b` model to have been installed separately by the operator.

## Commands

From the repository root:

```bash
bash scripts/start-ollama.sh
bash scripts/start-llamacpp.sh
wsl bash scripts/start-vllm.sh
wsl bash scripts/start-sglang.sh
```

To start or stop all configured Engines, use `bash scripts/start-all.sh` or `bash scripts/stop-all.sh`. Windows hosts can use `scripts/start-all.ps1` and `scripts/stop-all.ps1`; the latter invokes vLLM and SGLang through WSL.

The scripts match `config.toml`: Ollama uses port 11434 and `qwen3.5:9b`; llama.cpp uses 8080 and `qwen3.5-9b`; vLLM uses 8000 and `qwen3.5-9b`; SGLang uses 30000 and `qwen3.5-9b`.

Each stop script targets only its matching Engine process. The app never invokes these scripts.
