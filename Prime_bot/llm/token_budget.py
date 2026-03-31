import yaml

with open("config.yaml") as f:
    cfg = yaml.safe_load(f)

CONTEXT_WINDOW   = cfg["llm"].get("context_window", 8192)
THINK_OVERHEAD   = cfg["llm"].get("think_overhead", 1500)
OUTPUT_RESERVE   = cfg["llm"].get("output_reserve", 1800)
CHARS_PER_TOKEN  = 3.5

AVAILABLE_FOR_RAG = CONTEXT_WINDOW - THINK_OVERHEAD - OUTPUT_RESERVE


def chars_to_tokens(text: str) -> int:
    return int(len(text) / CHARS_PER_TOKEN)


def compute_top_k(
    system_prompt: str,
    history: str,
    extra: str = "",
    chunk_size: int = 500,
    max_top_k: int = 8,
    min_top_k: int = 2,
) -> int:
    committed_tokens = (
        chars_to_tokens(system_prompt)
        + chars_to_tokens(history)
        + chars_to_tokens(extra)
        + 200
    )
    tokens_for_rag = AVAILABLE_FOR_RAG - committed_tokens
    chunk_tokens   = int(chunk_size / CHARS_PER_TOKEN)
    top_k = max(min_top_k, min(max_top_k, tokens_for_rag // chunk_tokens))
    return int(top_k)
