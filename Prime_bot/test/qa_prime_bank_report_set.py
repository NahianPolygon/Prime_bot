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
    text, signals, done = collect_text(chat_flow.build_crew_stream(case.prompt, SessionMemory(f"report_{case.case_id}")))
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
        "done": done,
    }


def main():
    cases = [
        Case(
            "pb_docs_world",
            "For Mastercard World, list the salaried documents, self-employed documents, and say whether E-TIN is required.",
            "application",
            ["salary slip", "employment letter", "business registration", "itr", "e-tin"],
            ["lounge", "bogo"],
        ),
        Case(
            "pb_min_payment_world",
            "My Mastercard World outstanding is BDT 82,000. What minimum payment should I make this month?",
            "math",
            ["5,000"],
            [],
        ),
        Case(
            "pb_points_world",
            "If I spend BDT 125,000 every month on Mastercard World for a full year, how many reward points should I earn?",
            "math",
            ["60,000"],
            [],
        ),
        Case(
            "pb_third_companion",
            "With Mastercard World Balaka VIP, can I bring a third companion for free?",
            "benefit",
            ["2 companions"],
            [],
        ),
        Case(
            "pb_damaged_card",
            "My Prime Bank credit card is damaged but not lost. What should I do right now?",
            "service",
            ["nearest branch", "replacement"],
            [],
        ),
        Case(
            "pb_limit_history",
            "Without visiting a branch, how can I check my Prime Bank credit limit and transaction history?",
            "service",
            ["myprime", "credit limit", "transaction history"],
            [],
        ),
        Case(
            "pb_bogo_restaurants",
            "Can I use Visa Platinum BOGO at any restaurant, or only at specific partners?",
            "benefit",
            ["6 specified", "westin", "intercontinental"],
            [],
        ),
    ]
    print(json.dumps([run_case(case) for case in cases], indent=2))


if __name__ == "__main__":
    main()
