import yaml
import httpx
import time
from logging_utils import log_event

with open("config.yaml") as f:
    cfg = yaml.safe_load(f)


OLLAMA_BASE_URL = cfg["llm"].get("base_url", "http://localhost:11434")
OLLAMA_MODEL = cfg["llm"]["model"]


def chat(
    messages: list[dict],
    system: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 1200,
) -> str:
    started = time.perf_counter()
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "messages": [],
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }

    if system:
        payload["messages"].append({"role": "system", "content": system})

    payload["messages"].extend(messages)

    try:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            msg = data.get("message", {})
            content = msg.get("content", "").strip()
            log_event(
                "llm_call",
                model=OLLAMA_MODEL,
                base_url=OLLAMA_BASE_URL,
                temperature=temperature,
                prompt_messages=len(payload["messages"]),
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
