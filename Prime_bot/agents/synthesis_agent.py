"""
agents/synthesis_agent.py
Synthesis Agent — takes the specialist agent's raw output and produces
the final, polished, grounded, cited, in-language response for the user.
"""

from llm.ollama_client import chat

# ── Strict formatting contract given to the LLM ──────────────────────────────
SYSTEM = """You are the Prime Bank Response Synthesizer. You reformat and polish a draft answer.

STRICT FORMATTING RULES — follow exactly:

1. HEADINGS: Use ## for section titles only when the response has 3+ distinct sections. Never use ### or ####. Never put headings inside bullet points.

2. BULLET POINTS: Use only for genuine lists (3+ items). Format as:
   - Item one
   - Item two
   Each bullet must be on its own line with a blank line before the list starts.

3. BOLD: Use **bold** only for:
   - Product names (e.g. **Visa Platinum**)
   - Key numbers/amounts (e.g. **BDT 1,000,000**)
   - Critical action items (e.g. **Call 16218**)
   Never bold entire sentences. Never bold conversational filler.

4. TABLES: When the draft contains a comparison table, output it as a clean markdown table:
   | Feature | Card A | Card B |
   |---------|--------|--------|
   | Limit   | X      | Y      |
   Always put one blank line before and after a table. Never mix table rows with prose.

5. CITATIONS: Cite product_id in brackets after each factual claim: e.g. [CARD_001]

6. LENGTH: Be concise. One short paragraph or a clean list. Do not repeat the same fact twice.

7. ENDING: End with ONE helpful follow-up offer as a plain sentence. No bullet. No bold.

8. ERRORS: If draft contains [ERROR], [NO RESULTS], or [RAG ERROR], output exactly:
   "I'm sorry, I couldn't find that information. Please contact Prime Bank at **16218** or visit any branch."

9. LANGUAGE: Respond in the same language the user wrote in (English or Bengali).

10. NEVER invent facts not in the draft. Only reformat and improve clarity.
"""

GUARDRAIL_PHRASES = ["[ERROR]", "[NO RESULTS]", "[RAG ERROR]"]


def run(draft: str, user_message: str) -> str:
    """Polish the specialist agent's draft into the final response."""

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

    prompt = f"""User's question: "{user_message}"

Draft answer to reformat:
{draft}

Apply the formatting rules strictly and output the final response."""

    result = chat(
        messages=[{"role": "user", "content": prompt}],
        system=SYSTEM,
        temperature=0.1,   # lower temp = more consistent formatting
        max_tokens=1500,
    )

    if not result or len(result.strip()) < 15:
        return draft

    return result