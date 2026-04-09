import yaml
import httpx
import time
import re
from logging_utils import log_event

with open("config.yaml") as f:
    cfg = yaml.safe_load(f)

OLLAMA_BASE_URL = cfg["llm"].get("base_url", "http://localhost:11434")
OLLAMA_MODEL = cfg["llm"]["model"]
OLLAMA_KEEP_ALIVE = cfg["llm"].get("keep_alive", "5m")

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def chat(
    messages: list[dict],
    system: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 1200,
    think: bool = False,
) -> str:
    started = time.perf_counter()
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "keep_alive": OLLAMA_KEEP_ALIVE,
        "messages": [],
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }

    if not think:
        if system:
            system = system.rstrip() + "\n\n/no_think"
        else:
            system = "/no_think"

    if system:
        payload["messages"].append({"role": "system", "content": system})

    for msg in messages:
        payload["messages"].append({"role": msg["role"], "content": msg["content"]})

    try:
        with httpx.Client(timeout=180.0) as client:
            resp = client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            raw = data.get("message", {}).get("content", "").strip()
            content = _THINK_RE.sub("", raw).strip()
            if not content and raw:
                content = raw
            log_event(
                "llm_call",
                model=OLLAMA_MODEL,
                base_url=OLLAMA_BASE_URL,
                temperature=temperature,
                prompt_messages=len(payload["messages"]),
                raw_chars=len(raw),
                response_chars=len(content),
                latency_ms=round((time.perf_counter() - started) * 1000, 2),
            )
            return content
    except Exception as e:
        log_event(
            "llm_error",
            level="error",
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            error=str(e),
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
        )
        return f"[ERROR] LLM request failed: {e}"