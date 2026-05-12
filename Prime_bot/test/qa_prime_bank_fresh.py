from __future__ import annotations

import json
from dataclasses import dataclass

import chat_flow
from memory.session_memory import SessionMemory


def collect_text(gen):
    parts = []
    signals = []
    done = None
    for token in gen:
        if token.startswith('{"__'):
            try:
                obj = json.loads(token)
                signals.append(obj)
                if obj.get("__done_signal__"):
                    done = obj
            except Exception:
                parts.append(token)
        else:
            parts.append(token)
    return "".join(parts).strip(), signals, done


@dataclass
class Case:
    case_id: str
    prompt: str
    kind: str
    checks: list[str]
    rejects: list[str]


def run_case(case: Case) -> dict:
    session = SessionMemory(f"fresh_{case.case_id}")
    text, signals, done = collect_text(chat_flow.build_crew_stream(case.prompt, session))
    lowered = text.lower()
    failures = []

    if not text and not signals:
      failures.append("No assistant text or signal returned.")

    for needle in case.checks:
        if needle.lower() not in lowered:
            failures.append(f"Missing: {needle}")

    for needle in case.rejects:
        if needle.lower() in lowered:
            failures.append(f"Unexpected: {needle}")

    return {
        "case_id": case.case_id,
        "kind": case.kind,
        "prompt": case.prompt,
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "text": text[:700],
        "signals": signals,
        "done": done,
    }


def main():
    cases = [
        Case(
            "pb01_docs_mastercard_world",
            "For Mastercard World, list the salaried documents, self-employed documents, and say whether E-TIN is required.",
            "application",
            ["salary slip", "employment letter", "business registration", "itr", "e-tin"],
            ["lounge", "bogo"],
        ),
        Case(
            "pb02_min_payment_world",
            "My Mastercard World outstanding is BDT 82,000. What minimum payment should I make this month?",
            "math",
            ["5,000"],
            [],
        ),
        Case(
            "pb03_visa_platinum_loungekey",
            "For Prime Bank Visa Platinum, what exactly is included in LoungeKey and how does the USD 500 travel spend waiver work?",
            "benefit",
            ["1,400+", "usd 500", "premium lounges"],
            [],
        ),
        Case(
            "pb04_third_companion_world",
            "With Mastercard World Balaka VIP, can I bring a third companion for free?",
            "benefit",
            ["2 companions"],
            [],
        ),
        Case(
            "pb05_damaged_card",
            "My Prime Bank credit card is damaged but not lost. What should I do right now?",
            "service",
            ["nearest branch", "replacement"],
            [],
        ),
        Case(
            "pb06_limit_and_history",
            "Without visiting a branch, how can I check my Prime Bank credit limit and transaction history?",
            "service",
            ["myprime", "credit limit", "transaction history"],
            [],
        ),
        Case(
            "pb07_lost_card_abroad",
            "I lost my Prime Bank credit card while traveling abroad. Give me the international contact number only if you know it.",
            "service",
            ["+88022222222"],
            [],
        ),
        Case(
            "pb08_world_points_math",
            "If I spend BDT 125,000 every month on Mastercard World for a full year, how many reward points should I earn?",
            "math",
            ["60,000"],
            [],
        ),
        Case(
            "pb09_visa_platinum_two_visits",
            "For Visa Platinum, if I spend USD 1,000 during travel, how many LoungeKey visits should be waived?",
            "math",
            ["2 free visits"],
            [],
        ),
        Case(
            "pb10_bogo_restaurants",
            "Can I use Visa Platinum BOGO at any restaurant, or only at specific partners?",
            "benefit",
            ["6 specified", "westin", "intercontinental"],
            [],
        ),
    ]

    results = [run_case(case) for case in cases]
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
