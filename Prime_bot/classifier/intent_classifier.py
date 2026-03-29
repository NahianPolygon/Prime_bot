import yaml
import numpy as np
from sentence_transformers import SentenceTransformer

with open("config.yaml") as f:
    cfg = yaml.safe_load(f)

_model = SentenceTransformer(cfg["embeddings"]["model"])

INTENT_PROTOTYPES = {
    "i_need_a_credit_card": (
        "I want to apply for a new credit card, get card recommendations, "
        "compare different cards, which card is best for me, "
        "I am looking for a credit card, help me choose a card"
    ),
    "existing_cardholder": (
        "I already have a credit card, help me with my existing card, "
        "lost card, card stolen, block my card, activate card, "
        "bill payment, statement, outstanding balance, reward points redemption, "
        "increase credit limit on my existing card"
    ),
    "eligibility_check": (
        "am I eligible, can I apply, do I qualify, what are the requirements, "
        "what income do I need, what documents are needed, who can apply, "
        "age requirement, employment requirement, can I get a card"
    ),
    "comparison": (
        "compare cards, difference between, which is better, "
        "versus, vs, contrast, side by side comparison of cards"
    ),
    "catalog_query": (
        "how many cards, list all cards, what cards does prime bank have, "
        "show me all products, types of cards available, "
        "how many visa cards, how many mastercard, how many islamic cards, "
        "what are the available credit cards"
    ),
    "faq_compliance": (
        "fees, charges, annual fee, interest rate, late payment, "
        "terms and conditions, how to apply, application process, "
        "documents required, what is the process"
    ),
}

BANKING_PROTOTYPES = {
    "conventional": (
        "regular bank, standard banking, conventional, normal interest-based, "
        "visa gold, visa platinum, mastercard, standard credit card"
    ),
    "islami": (
        "Islamic bank, halal, shariah, riba-free, ujrah, hasanah, "
        "Islamic finance, interest free, Muslim banking, sharia compliant"
    ),
}

_intent_embs = {k: _model.encode(v) for k, v in INTENT_PROTOTYPES.items()}
_banking_embs = {k: _model.encode(v) for k, v in BANKING_PROTOTYPES.items()}


def classify(user_message: str) -> dict:
    q = _model.encode(user_message)

    intent_scores = {
        k: float(np.dot(q, v) / (np.linalg.norm(q) * np.linalg.norm(v) + 1e-9))
        for k, v in _intent_embs.items()
    }
    banking_scores = {
        k: float(np.dot(q, v) / (np.linalg.norm(q) * np.linalg.norm(v) + 1e-9))
        for k, v in _banking_embs.items()
    }

    best_intent = max(intent_scores, key=intent_scores.__getitem__)
    best_banking = max(banking_scores, key=banking_scores.__getitem__)

    return {
        "intent": best_intent,
        "banking_type": best_banking,
        "intent_score": intent_scores[best_intent],
        "banking_score": banking_scores[best_banking],
        "all_intent_scores": intent_scores,
    }


if __name__ == "__main__":
    tests = [
        "I want to apply for a halal credit card",
        "I lost my card, please block it",
        "compare Visa Gold and Hasanah Gold",
        "how many Islamic credit cards do you have?",
        "am I eligible for a platinum card?",
        "what is the annual fee for Visa Gold?",
    ]
    for t in tests:
        r = classify(t)
        print(f"\nQ: {t}")
        print(
            f"   intent={r['intent']} ({r['intent_score']:.2f})  "
            f"banking={r['banking_type']} ({r['banking_score']:.2f})"
        )
