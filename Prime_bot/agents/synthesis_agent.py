from llm.ollama_client import chat
import re

SYSTEM = """You are the Prime Bank Response Synthesizer.
You receive a draft answer from a specialist agent and refine it into the final user-facing response.

Your job:
1. Keep responses user-friendly and do not expose internal product_id codes unless the user explicitly asks for reference IDs
2. Format clearly: use bullet points for lists
3. Use markdown tables only when the user explicitly asks to compare products (compare, vs, versus, difference, which is better)
4. Remove any LLM artifacts, repetition, or filler phrases
5. Ensure the tone is professional, warm, and helpful - like a senior bank advisor
6. Add a single helpful follow-up offer at the end if appropriate
7. If the draft says "[ERROR]" or has no real content, replace with:
   "I'm sorry, I couldn't find that information. Please contact Prime Bank at **16218** or visit any branch."
8. NEVER add new facts not present in the draft - only improve clarity and formatting
9. Respond in the same language the user wrote in (English or Bengali/Bangla)
"""

GUARDRAIL_PHRASES = [
    "[ERROR]",
    "[NO RESULTS]",
    "[RAG ERROR]",
]


def _strip_product_ids(text: str) -> str:
    cleaned = re.sub(r"\[?[A-Z]+(?:_[A-Z]+)*_\d+\]?", "", text)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def run(draft: str, user_message: str) -> str:
    if not draft or len(draft.strip()) < 15:
        return (
            "I'm sorry, I couldn't find relevant information for your query. "
            "Please contact Prime Bank at **16218** or visit any branch for assistance."
        )

    for phrase in GUARDRAIL_PHRASES:
        if phrase in draft:
            return (
                "I'm sorry, I couldn't find that information in my knowledge base. "
                "Please contact Prime Bank at **16218** or visit any branch."
            )

    prompt = f"""User's original question: \"{user_message}\"

Specialist agent draft response:
{draft}

Refine this into the final polished response. Improve formatting and ensure citations are present.
If the question is not an explicit comparison request, do not use a markdown table.
Do not add any new facts."""

    result = chat(
        messages=[{"role": "user", "content": prompt}],
        system=SYSTEM,
        temperature=0.2,
        max_tokens=1200,
    )

    if not result or len(result.strip()) < 15:
        return _strip_product_ids(draft)

    return _strip_product_ids(result)
