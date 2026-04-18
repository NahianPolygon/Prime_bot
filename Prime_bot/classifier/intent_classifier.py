import json
import re
from llm.ollama_client import chat


SYSTEM_ROUTE = """You route messages for a Prime Bank credit card assistant.

Return ONLY JSON with this schema:
{"category":"new_card"|"existing_card","sub_intent":"catalog"|"discover"|"compare"|"eligibility"|"apply"|"details"|"existing_card","banking_type":"conventional"|"islami"|"both","confidence":0.0,"calculator":""}

Field definitions:
- category=new_card for browsing, recommendations, comparisons, eligibility, application help, card details, or general new-card questions
- category=existing_card for cardholder support such as billing, statements, activation, PIN, rewards redemption, lost/stolen card, limit increase, EMI conversion, or service issues
- sub_intent=catalog when the user wants to see available cards or browse the lineup
- sub_intent=discover when the user wants recommendations based on needs, lifestyle, or preferences
- sub_intent=compare when the user wants to compare cards
- sub_intent=eligibility when the user wants to check qualification or requirements
- sub_intent=apply when the user wants application steps, documents, or process
- sub_intent=details when the user wants information about one specific card
- sub_intent=existing_card only when category=existing_card
- banking_type=islami for Islamic, Shariah-compliant, halal, Hasanah, or riba-free requests
- banking_type=conventional for standard non-Islamic cards
- banking_type=both when unclear, mixed, or not specified
- confidence: number 0.0-1.0 — your confidence in this classification
  Use 0.9-1.0 for clear unambiguous banking queries
  Use 0.6-0.8 for reasonable but somewhat ambiguous queries
  Use 0.3-0.5 for very short, ambiguous, or multi-purpose messages (single words, greetings, unclear topic)
- calculator: "emi" when user explicitly asks to calculate EMI amounts, monthly installment payments, or 0% installment plan cost
              "rewards" when user explicitly asks to calculate reward point earnings, redemption values, or how many points they would earn
              "" in all other cases (do not set calculator for general questions about EMI or rewards that don't ask for a calculation)

Intent guidance:
- Messages about lost card, stolen card, blocked card, PIN, statement, bill payment, due amount, credit limit, activation, rewards redemption, card delivery, card not working, charge dispute, EMI conversion after purchase, or other cardholder servicing are existing_card
- Messages about wanting a card, choosing among cards, comparing cards, checking qualification, browsing products, asking features, annual fees, lounge access, rewards, insurance, or how to apply are new_card
- If the current message is short or ambiguous, use the conversation context to decide whether the user is continuing a browsing flow or switching to servicing
- If the message clearly names two or more cards or asks "compare", use sub_intent=compare
- If the message asks whether the user qualifies, is eligible, can get approved, or meets requirements, use sub_intent=eligibility
- If the message asks details of one specific card, use sub_intent=details even if the wording is casual

Examples:
- "I lost my card" -> {"category":"existing_card","sub_intent":"existing_card","banking_type":"both","confidence":0.98,"calculator":""}
- "my card is blocked" -> {"category":"existing_card","sub_intent":"existing_card","banking_type":"both","confidence":0.98,"calculator":""}
- "stolen or lost card" -> {"category":"existing_card","sub_intent":"existing_card","banking_type":"both","confidence":0.95,"calculator":""}
- "help me activate my Hasanah card" -> {"category":"existing_card","sub_intent":"existing_card","banking_type":"islami","confidence":0.97,"calculator":""}
- "how do I set up card PIN" -> {"category":"existing_card","sub_intent":"existing_card","banking_type":"both","confidence":0.95,"calculator":""}
- "I need my statement and bill payment options" -> {"category":"existing_card","sub_intent":"existing_card","banking_type":"both","confidence":0.96,"calculator":""}
- "can I increase credit limit on my card" -> {"category":"existing_card","sub_intent":"existing_card","banking_type":"both","confidence":0.94,"calculator":""}
- "how much would my EMI be for 50000 BDT over 12 months?" -> {"category":"existing_card","sub_intent":"existing_card","banking_type":"both","confidence":0.92,"calculator":"emi"}
- "how many reward points would I earn on 30000 BDT monthly spend?" -> {"category":"existing_card","sub_intent":"existing_card","banking_type":"both","confidence":0.90,"calculator":"rewards"}
- "show me halal cards" -> {"category":"new_card","sub_intent":"catalog","banking_type":"islami","confidence":0.95,"calculator":""}
- "What credit cards does Prime Bank offer?" -> {"category":"new_card","sub_intent":"catalog","banking_type":"both","confidence":0.97,"calculator":""}
- "show me conventional cards" -> {"category":"new_card","sub_intent":"catalog","banking_type":"conventional","confidence":0.96,"calculator":""}
- "Islamic / Halal please" -> {"category":"new_card","sub_intent":"catalog","banking_type":"islami","confidence":0.90,"calculator":""}
- "show me Visa Gold and JCB Gold options" -> {"category":"new_card","sub_intent":"catalog","banking_type":"conventional","confidence":0.92,"calculator":""}
- "tell me about Visa Hasanah Gold" -> {"category":"new_card","sub_intent":"details","banking_type":"islami","confidence":0.97,"calculator":""}
- "tell me about Mastercard World Credit Card" -> {"category":"new_card","sub_intent":"details","banking_type":"conventional","confidence":0.97,"calculator":""}
- "what is JCB Gold Credit Card?" -> {"category":"new_card","sub_intent":"details","banking_type":"conventional","confidence":0.95,"calculator":""}
- "does Visa Platinum have lounge access?" -> {"category":"new_card","sub_intent":"details","banking_type":"conventional","confidence":0.95,"calculator":""}
- "can I get Mastercard World" -> {"category":"new_card","sub_intent":"eligibility","banking_type":"conventional","confidence":0.88,"calculator":""}
- "Check my eligibility" -> {"category":"new_card","sub_intent":"eligibility","banking_type":"both","confidence":0.97,"calculator":""}
- "Am I eligible for Mastercard World Credit Card?" -> {"category":"new_card","sub_intent":"eligibility","banking_type":"conventional","confidence":0.97,"calculator":""}
- "can I apply for the halal gold card?" -> {"category":"new_card","sub_intent":"apply","banking_type":"islami","confidence":0.93,"calculator":""}
- "how to apply for Visa Gold Credit Card" -> {"category":"new_card","sub_intent":"apply","banking_type":"conventional","confidence":0.96,"calculator":""}
- "compare Visa Gold and JCB Gold" -> {"category":"new_card","sub_intent":"compare","banking_type":"conventional","confidence":0.97,"calculator":""}
- "which is better, Visa Hasanah Platinum or Visa Hasanah Gold?" -> {"category":"new_card","sub_intent":"compare","banking_type":"islami","confidence":0.96,"calculator":""}
- "hi" -> {"category":"new_card","sub_intent":"discover","banking_type":"both","confidence":0.35,"calculator":""}
- "ok" -> {"category":"new_card","sub_intent":"discover","banking_type":"both","confidence":0.30,"calculator":""}

Use the conversation context if provided. Infer semantically. Do not explain anything outside the JSON."""


VALID_ENTRY = {"new_card", "existing_card"}
VALID_SUB = {"catalog", "discover", "compare", "eligibility", "apply", "details", "existing_card"}
VALID_BANKING = {"conventional", "islami", "both"}

INTENT_MAP = {
    "catalog": "catalog_query",
    "discover": "i_need_a_credit_card",
    "compare": "comparison",
    "eligibility": "eligibility_check",
    "apply": "how_to_apply",
    "details": "product_details",
    "existing_card": "existing_cardholder",
}


def _parse_json(text: str) -> dict:
    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    match = re.search(r"\{[^{}]*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            return {}
    return {}


def classify(user_message: str, history: str = "") -> dict:
    if history:
        context_msg = f"""Recent conversation:
{history}

Current message: {user_message}"""
    else:
        context_msg = user_message

    parsed = {}
    for _ in range(2):
        parsed = _parse_json(
            chat(
                messages=[{"role": "user", "content": context_msg}],
                system=SYSTEM_ROUTE,
                temperature=0.0,
                max_tokens=220,
            )
        )
        if parsed:
            break

    category = parsed.get("category", "new_card")
    if category not in VALID_ENTRY:
        category = "new_card"

    sub_intent = parsed.get("sub_intent", "discover")
    if category == "existing_card":
        sub_intent = "existing_card"
    elif sub_intent not in VALID_SUB:
        sub_intent = "discover"

    banking_type = parsed.get("banking_type", "both")
    if banking_type not in VALID_BANKING:
        banking_type = "both"

    try:
        confidence = float(parsed.get("confidence", 0.9))
        confidence = max(0.0, min(1.0, confidence))
    except (ValueError, TypeError):
        confidence = 0.9

    raw_calc = parsed.get("calculator", "")
    calculator_type = raw_calc if raw_calc in ("emi", "rewards") else ""

    return {
        "intent": INTENT_MAP[sub_intent],
        "banking_type": banking_type,
        "intent_score": confidence,
        "banking_score": 0.90,
        "all_intent_scores": {},
        "calculator_type": calculator_type,
    }
