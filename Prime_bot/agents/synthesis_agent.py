import re
from typing import Generator
from llm.ollama_client import chat, chat_stream

SYSTEM = """You are the Prime Bank Response Synthesizer. You clean up and reformat a draft answer.

Rules:
1. Use ## headings only for 3+ sections. Never use ### or ####.
2. Use bullet points only for lists of 3+ items.
3. Bold only: product names, key amounts, critical actions like **Call 16218**.
4. Output comparison tables as clean markdown tables with blank lines before and after.
5. Remove any product_id, internal IDs, or system codes like CARD_001, ISLAMI_CARD_002. Replace them with the actual card name from context or remove entirely.
6. Be concise. Do not repeat facts.
7. End with one helpful follow-up sentence.
8. Respond in the same language the user wrote in.
9. NEVER add facts not in the draft. Only reformat.
"""

GUARDRAIL_PHRASES = ["[ERROR]", "[NO RESULTS]", "[RAG ERROR]"]

FALLBACK = (
    "I'm sorry, I couldn't find relevant information for your query. "
    "Please contact Prime Bank at **16218** or visit any branch for assistance."
)

_CITATION_RE = re.compile(r'\$?(?:CARD_|ISLAMI_CARD_)\d+\$?')
_TABLE_RE = re.compile(r'\|.+\|')
_PRODUCT_ID_RE = re.compile(r'\(?product_id[:\s]*[A-Z_0-9]+\)?', re.IGNORECASE)
_INTERNAL_CODE_RE = re.compile(r'\b(?:ISLAMI_CARD|CARD)_\d+\b')


def _strip_product_ids(text: str) -> str:
    text = _PRODUCT_ID_RE.sub('', text)
    text = _CITATION_RE.sub('', text)
    text = _INTERNAL_CODE_RE.sub('', text)
    text = re.sub(r'\$\s*\$', '', text)
    text = re.sub(r'\|\s*\|', '| N/A |', text)
    text = re.sub(r'  +', ' ', text)
    return text.strip()


def _has_internal_codes(text: str) -> bool:
    return bool(_INTERNAL_CODE_RE.search(text)) or bool(_PRODUCT_ID_RE.search(text))


def _draft_is_clean(draft: str) -> bool:
    if _has_internal_codes(draft):
        return False
    has_table = bool(_TABLE_RE.search(draft))
    reasonable_length = 80 < len(draft) < 3000
    if reasonable_length:
        return True
    if has_table:
        return True
    return False


def _build_prompt(draft: str, user_message: str) -> str:
    return f"""User question: "{user_message}"

Draft to reformat:
{draft}

Reformat this draft. Do not add any new information. Remove any product_id or internal codes like CARD_001 or ISLAMI_CARD_002. Replace them with the actual card name from context or remove the reference entirely."""


def run(draft: str, user_message: str) -> str:
    if not draft or len(draft.strip()) < 15:
        return FALLBACK

    for phrase in GUARDRAIL_PHRASES:
        if phrase in draft:
            return FALLBACK

    draft = _strip_product_ids(draft)

    if not draft or len(draft.strip()) < 15:
        return FALLBACK

    if _draft_is_clean(draft):
        return draft

    prompt = _build_prompt(draft, user_message)

    result = chat(
        messages=[{"role": "user", "content": prompt}],
        system=SYSTEM,
        temperature=0.1,
        max_tokens=1500,
    )

    if not result or len(result.strip()) < 15:
        return draft

    result = _strip_product_ids(result)

    if not result or len(result.strip()) < 15:
        return draft

    return result


def run_stream(draft: str, user_message: str) -> Generator[str, None, None]:
    if not draft or len(draft.strip()) < 15:
        yield FALLBACK
        return

    for phrase in GUARDRAIL_PHRASES:
        if phrase in draft:
            yield FALLBACK
            return

    draft = _strip_product_ids(draft)

    if not draft or len(draft.strip()) < 15:
        yield FALLBACK
        return

    if _draft_is_clean(draft):
        yield draft
        return

    prompt = _build_prompt(draft, user_message)

    for token in chat_stream(
        messages=[{"role": "user", "content": prompt}],
        system=SYSTEM,
        temperature=0.1,
        max_tokens=1500,
    ):
        yield token