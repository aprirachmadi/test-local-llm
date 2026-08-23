# OpenAI-compatible API is the only engine seam

Status: accepted

The chatbot must work against multiple local serving engines (Ollama, vLLM, SGLang, llama.cpp, and any future ones) without per-engine code. We decided that every Engine is consumed exclusively through the OpenAI-compatible `/v1/chat/completions` HTTP API, and that an Engine is therefore a pure config entry in `config.toml` (`name`, `base_url`, `model`, `enabled`) — no per-engine adapters, no official engine SDKs.

**Considered options**: per-engine native adapters (ollama-python, vLLM client, SGLang client, …), rejected because every new engine would cost code and the app would stop being generic.

**Consequences**: adding an engine is a config change, not a code change; cross-engine behavior is defined by the OpenAI surface, so engine-specific features (model registries, GPU offload knobs) are out of scope for the core loop and may only be added later as opt-in extensions. Engines without an OpenAI-compatible endpoint are out of scope by definition.
