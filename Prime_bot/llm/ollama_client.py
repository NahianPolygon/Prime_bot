import yaml
import httpx
import time
import re
import json
from typing import Generator
from logging_utils import log_event

with open("config.yaml") as f:
    cfg = yaml.safe_load(f)

OLLAMA_BASE_URL = cfg["llm"].get("base_url", "http://localhost:11434")
OLLAMA_MODEL = cfg["llm"]["model"]
OLLAMA_KEEP_ALIVE = cfg["llm"].get("keep_alive", "5m")

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def _build_payload(
    messages: list[dict],
    system: str | None,
    temperature: float,
    max_tokens: int,
    think: bool,
    stream: bool,
) -> dict:
    payload = {
        "model": OLLAMA_MODEL,
        "stream": stream,
        "think": think,
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

    return payload


def chat(
    messages: list[dict],
    system: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 1200,
    think: bool = False,
) -> str:
    started = time.perf_counter()
    payload = _build_payload(messages, system, temperature, max_tokens, think, stream=False)

    try:
        with httpx.Client(timeout=180.0) as client:
            resp = client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            message = data.get("message", {}) or {}
            raw = (message.get("content") or data.get("response") or "").strip()
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


def chat_stream(
    messages: list[dict],
    system: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 1200,
    think: bool = False,
) -> Generator[str, None, None]:
    started = time.perf_counter()
    payload = _build_payload(messages, system, temperature, max_tokens, think, stream=True)

    in_think_block = False
    total_chars = 0

    try:
        with httpx.Client(timeout=180.0) as client:
            with client.stream(
                "POST",
                f"{OLLAMA_BASE_URL}/api/chat",
                json=payload,
                timeout=180.0,
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    message = chunk.get("message", {}) or {}
                    token = message.get("content", "")
                    if not token:
                        if chunk.get("done"):
                            break
                        continue

                    if "<think>" in token:
                        in_think_block = True
                        token = token.split("<think>")[0]
                        if token:
                            total_chars += len(token)
                            yield token
                        continue

                    if "</think>" in token:
                        in_think_block = False
                        token = token.split("</think>")[-1]
                        if token:
                            total_chars += len(token)
                            yield token
                        continue

                    if in_think_block:
                        continue

                    total_chars += len(token)
                    yield token

                    if chunk.get("done"):
                        break

        log_event(
            "llm_stream_complete",
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=temperature,
            prompt_messages=len(payload["messages"]),
            response_chars=total_chars,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
        )
    except Exception as e:
        log_event(
            "llm_stream_error",
            level="error",
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            error=str(e),
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
        )
        yield f"[ERROR] LLM stream failed: {e}"
