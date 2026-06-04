import os
from typing import Optional

from app.adapters.llm import OllamaAdapter, OllamaSettings

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://192.168.65.254:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
_OLLAMA_SEED_RAW = str(os.getenv("OLLAMA_SEED", "")).strip()
OLLAMA_SEED: Optional[int] = int(_OLLAMA_SEED_RAW) if _OLLAMA_SEED_RAW else None
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.6"))
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "8192"))
OLLAMA_REPEAT_PENALTY = float(os.getenv("OLLAMA_REPEAT_PENALTY", "1.18"))
OLLAMA_REPEAT_LAST_N = int(os.getenv("OLLAMA_REPEAT_LAST_N", "192"))
OLLAMA_TIMEOUT_SEC = int(os.getenv("OLLAMA_TIMEOUT_SEC", "240"))
OLLAMA_ADAPTER = OllamaAdapter(
    OllamaSettings(
        url=OLLAMA_URL,
        model=OLLAMA_MODEL,
        timeout_sec=OLLAMA_TIMEOUT_SEC,
        seed=OLLAMA_SEED,
        temperature=OLLAMA_TEMPERATURE,
        num_ctx=OLLAMA_NUM_CTX,
        repeat_penalty=OLLAMA_REPEAT_PENALTY,
        repeat_last_n=OLLAMA_REPEAT_LAST_N,
    )
)
