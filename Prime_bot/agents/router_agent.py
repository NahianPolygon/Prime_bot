from memory.session_memory import SessionMemory


def run(
    user_message: str,
    classifier_output: dict,
    session: SessionMemory,
) -> dict:
    intent = classifier_output["intent"]
    banking = classifier_output["banking_type"]

    if banking == "both":
        collection = "all_products"
    elif intent in ("i_need_a_credit_card", "how_to_apply", "product_details"):
        collection = f"{banking}_credit_i_need_a_credit_card"
    elif intent == "existing_cardholder":
        collection = f"{banking}_credit_existing_cardholder"
    else:
        collection = "all_products"

    return {
        "intent": intent,
        "banking_type": banking,
        "collection": collection,
        "search_query": user_message,
    }