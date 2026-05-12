import json
import uuid

from chat_flow import build_crew
from memory.session_memory import SessionMemory


TESTS = [
    {
        "id": "R2_GREETING_01",
        "section": "greeting",
        "question": "Hello there",
        "expected_any": ["hello", "credit card"],
    },
    {
        "id": "R2_CATALOG_01",
        "section": "catalog",
        "question": "Which Mastercard credit cards are available from Prime Bank?",
        "expected_any": ["mastercard platinum", "mastercard world"],
    },
    {
        "id": "R2_CATALOG_02",
        "section": "catalog",
        "question": "List only the JCB credit cards offered by Prime Bank.",
        "expected_any": ["jcb gold", "jcb platinum"],
    },
    {
        "id": "R2_DETAILS_01",
        "section": "product_details",
        "question": "How many companions can use Balaka VIP with Mastercard World Credit Card?",
        "expected_any": ["2 companions", "two companions"],
    },
    {
        "id": "R2_DETAILS_02",
        "section": "product_details",
        "question": "What is the Airport Welcome booking contact for Mastercard World Credit Card?",
        "expected_any": ["01974 444 555", "01822 991 111", "mga.dhaka@gmail.com"],
    },
    {
        "id": "R2_DETAILS_03",
        "section": "product_details",
        "question": "What is the difference between LoungeKey and Priority Pass on Mastercard Platinum Credit Card?",
        "expected_any": ["priority pass", "loungekey"],
    },
    {
        "id": "R2_APPLY_01",
        "section": "apply",
        "question": "For Mastercard World Credit Card, what identity, income, financial, and nominee documents are required?",
        "expected_any": ["nid/passport", "salary", "e-tin", "nominee"],
    },
    {
        "id": "R2_APPLY_02",
        "section": "apply",
        "question": "What are the salaried and self-employed requirements for JCB Gold Credit Card application?",
        "expected_any": ["salaried", "self-employed", "salary slip", "trade license"],
    },
    {
        "id": "R2_SERVICE_01",
        "section": "existing_cardholder",
        "question": "How do I activate a renewed Hasanah credit card?",
        "expected_any": ["card-activation", "activation portal"],
    },
    {
        "id": "R2_SERVICE_02",
        "section": "existing_cardholder",
        "question": "How can I reset the PIN of my Hasanah card?",
        "expected_any": ["myprime", "generate-card-pin-with-myprime"],
    },
    {
        "id": "R2_SERVICE_03",
        "section": "existing_cardholder",
        "question": "If my conventional Prime Bank card is damaged, what should I do?",
        "expected_any": ["nearest branch", "replacement"],
    },
    {
        "id": "R2_SERVICE_04",
        "section": "existing_cardholder",
        "question": "How do I endorse my Hasanah card for foreign currency transactions?",
        "expected_any": ["valid passport", "branch", "endorse"],
    },
    {
        "id": "R2_SERVICE_05",
        "section": "existing_cardholder",
        "question": "Without visiting a branch, how can I check limit and transaction history for my credit card?",
        "expected_any": ["myprime", "transaction history", "limit"],
    },
    {
        "id": "R2_SERVICE_06",
        "section": "existing_cardholder",
        "question": "What cardholder privilege links are available for conventional Prime Bank cards?",
        "expected_any": ["year-round-discount", "emi-discount"],
    },
    {
        "id": "R2_MATH_01",
        "section": "calculations",
        "question": "If I spend BDT 62,500 every month on Mastercard World Credit Card, how many reward points will I earn in a year?",
        "expected_any": ["30,000", "30000"],
    },
    {
        "id": "R2_MATH_02",
        "section": "calculations",
        "question": "If I spend BDT 87,500 per month on Mastercard World, how many months will it take to reach 15,000 reward points?",
        "expected_any": ["5 month", "five month"],
    },
    {
        "id": "R2_MATH_03",
        "section": "calculations",
        "question": "If I convert BDT 1,000,000 on JCB Platinum Credit Card into a 24-month EMI, what is the monthly installment?",
        "expected_any": ["41,667", "41667"],
    },
    {
        "id": "R2_MATH_04",
        "section": "calculations",
        "question": "My JCB Gold statement was generated on February 10. What is the last interest-free payment date?",
        "expected_any": ["april 1", "2026-04-01"],
    },
    {
        "id": "R2_MATH_05",
        "section": "calculations",
        "question": "If my JCB Gold outstanding balance is BDT 1,35,000 and the monthly interest rate is 1.5%, how much interest will I owe after one month?",
        "expected_any": ["2,025", "2025"],
    },
    {
        "id": "R2_MATH_06",
        "section": "calculations",
        "question": "If I use JCB Platinum BOGO twice a month and each meal costs BDT 4,250, how much do I save in a year?",
        "expected_any": ["102,000", "102000"],
    },
    {
        "id": "R2_MATH_07",
        "section": "calculations",
        "question": "For Visa Hasanah Gold Credit Card, if I buy a laptop worth BDT 150,000 on 0% EMI over 24 months, what will the monthly installment be?",
        "expected_any": ["6,250", "6250"],
    },
]


def main() -> None:
    results = []
    for test in TESTS:
        session = SessionMemory(str(uuid.uuid4()))
        answer = build_crew(test["question"], session)
        lowered = answer.lower()
        hits = [needle for needle in test["expected_any"] if needle.lower() in lowered]
        results.append(
            {
                "id": test["id"],
                "section": test["section"],
                "question": test["question"],
                "expected_any": test["expected_any"],
                "matched": hits,
                "passed": bool(hits),
                "answer": answer,
            }
        )
        print(f'[{test["id"]}] passed={bool(hits)} matched={hits}')
    print("\n===JSON===")
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
