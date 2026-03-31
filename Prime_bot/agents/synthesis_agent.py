import re
from llm.ollama_client import chat

SYSTEM = """You are the Prime Bank Response Synthesizer. You clean up and reformat a draft answer.

Rules:
1. Use ## headings only for 3+ sections. Never use ### or ####.
2. Use bullet points only for lists of 3+ items.
3. Bold only: product names, key amounts, critical actions like **Call 16218**.
4. Output comparison tables as clean markdown tables with blank lines before and after.
5. Keep citations in brackets: [CARD_001]
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

_CITATION_RE = re.compile(r'$$(?:CARD_|ISLAMI_CARD_)\d+$$')
_TABLE_RE = re.compile(r'\|.+\|')


def _draft_is_clean(draft: str) -> bool:
    has_citations = bool(_CITATION_RE.search(draft))
    has_table = bool(_TABLE_RE.search(draft))
    reasonable_length = 80 < len(draft) < 2000
    if has_citations and reasonable_length:
        return True
    if has_table and reasonable_length:
        return True
    return False


def run(draft: str, user_message: str) -> str:
    if not draft or len(draft.strip()) < 15:
        return FALLBACK

    for phrase in GUARDRAIL_PHRASES:
        if phrase in draft:
            return FALLBACK

    if _draft_is_clean(draft):
        return draft

    prompt = f"""User question: "{user_message}"

Draft to reformat:
{draft}

Reformat this draft. Do not add any new information."""

    result = chat(
        messages=[{"role": "user", "content": prompt}],
        system=SYSTEM,
        temperature=0.1,
        max_tokens=1500,
    )

    if not result or len(result.strip()) < 15:
        return draft

    return result