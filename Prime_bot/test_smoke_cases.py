from __future__ import annotations

import json

import agents.compliance_faq as compliance_faq
from memory.session_memory import SessionMemory
import chat_flow


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


def run_case(name, fn):
    try:
        out = fn()
        print(f"[PASS] {name}: {out}")
    except Exception as exc:
        print(f"[FAIL] {name}: {exc}")


def main():
    run_case(
        "greeting",
        lambda: collect_text(chat_flow.build_crew_stream("Hello", SessionMemory("t1")))[0][:160],
    )
    run_case(
        "catalog_query",
        lambda: collect_text(chat_flow.build_crew_stream("What credit cards do you offer?", SessionMemory("t2")))[0][:220],
    )

    def discovery_form():
        _, signals, _ = collect_text(chat_flow.build_crew_stream("I want a halal credit card", SessionMemory("t3")))
        form = next((s for s in signals if s.get("__preference_form_signal__")), None)
        assert form is not None, "preference form not shown"
        return str(form["schema"].get("prefill"))

    run_case("discovery_form", discovery_form)

    def prefill_from_query():
        _, signals, _ = collect_text(
            chat_flow.build_crew_stream(
                "I am 30 years old. I earn 100 k per month. Which shariah based credit card will be most suitable for me?",
                SessionMemory("t4"),
            )
        )
        form = next((s for s in signals if s.get("__preference_form_signal__")), None)
        assert form is not None, "preference form not shown"
        prefill = form["schema"].get("prefill", {})
        assert prefill.get("banking_type") == "islami", prefill
        assert prefill.get("income_band") == "100k_200k", prefill
        return str(prefill)

    run_case("prefill_from_query", prefill_from_query)

    def eligibility_scope_preserved():
        text = """
Mastercard World Credit Card
✅ Likely Eligible
Age: ✅ 40 years
E-TIN: ✅ Yes

Mastercard Platinum Credit Card
❌ Likely Ineligible
Age: ✅ 40 years
E-TIN: ✅ Yes

Alternative options you may consider: Visa Gold Credit Card, JCB Gold Credit Card
""".strip()
        verdicts = compliance_faq.extract_eligibility_verdicts(
            text,
            scoped_cards=["Mastercard World Credit Card", "Mastercard Platinum Credit Card"],
        )
        names = [item.get("card_name") for item in verdicts]
        assert names == ["Mastercard World Credit Card", "Mastercard Platinum Credit Card"], names
        return str(names)

    run_case("eligibility_scope_preserved", eligibility_scope_preserved)

    def recommendation_submit():
        session = SessionMemory("t5")
        text = chat_flow.handle_preference_form(
            {
                "banking_type": "conventional",
                "use_case": "business_spending",
                "income_band": "200k_plus",
                "travel_frequency": "frequent",
                "tier_preference": "premium",
            },
            session,
        )
        cards = session.user_profile.get("recommended_cards")
        assert len(text) > 120, "short recommendation"
        assert cards, "no recommended cards remembered"
        return str(cards)

    run_case("recommendation_submit", recommendation_submit)

    def eligibility_form_followup():
        session = SessionMemory("t6")
        chat_flow.handle_preference_form(
            {
                "banking_type": "conventional",
                "use_case": "business_spending",
                "income_band": "200k_plus",
                "travel_frequency": "frequent",
                "tier_preference": "premium",
            },
            session,
        )
        _, signals, _ = collect_text(chat_flow.build_crew_stream("Check my eligibility", session))
        form = next((s for s in signals if s.get("__form_signal__")), None)
        assert form is not None, "eligibility form not shown"
        schema = form["schema"]
        return f"target={schema.get('target_card', '')} recommended={schema.get('recommended_cards')}"

    run_case("eligibility_form_followup", eligibility_form_followup)

    def eligibility_submit():
        session = SessionMemory("t7")
        chat_flow.handle_preference_form(
            {
                "banking_type": "conventional",
                "use_case": "business_spending",
                "income_band": "200k_plus",
                "travel_frequency": "frequent",
                "tier_preference": "premium",
            },
            session,
        )
        chat_flow.handle_eligibility_form(
            {
                "age": 50,
                "employment_type": "business_owner",
                "monthly_income": 900000,
                "employment_duration_years": 15,
                "employment_duration_months": 9,
                "has_etin": True,
            },
            session,
        )
        verdicts = session.user_profile.get("last_eligibility_verdicts") or []
        assert verdicts, "no verdicts parsed"
        return str(verdicts[:2])

    run_case("eligibility_submit", eligibility_submit)

    def comparison_followup():
        session = SessionMemory("t8")
        chat_flow.handle_preference_form(
            {
                "banking_type": "conventional",
                "use_case": "business_spending",
                "income_band": "200k_plus",
                "travel_frequency": "frequent",
                "tier_preference": "premium",
            },
            session,
        )
        text, _, _ = collect_text(chat_flow.build_crew_stream("Compare with another card", session))
        assert "|" in text or "Feature" in text, "comparison table not found"
        return text[:220]

    run_case("comparison_followup", comparison_followup)

    def fees_followup():
        session = SessionMemory("t9")
        chat_flow.handle_preference_form(
            {
                "banking_type": "conventional",
                "use_case": "business_spending",
                "income_band": "200k_plus",
                "travel_frequency": "frequent",
                "tier_preference": "premium",
            },
            session,
        )
        collect_text(chat_flow.build_crew_stream("Compare with another card", session))
        text, _, _ = collect_text(chat_flow.build_crew_stream("Explain the fees", session))
        assert len(text) > 60, "fees response too short"
        assert "Visa Platinum" in text and "Mastercard Platinum" in text, "fees follow-up lost multi-card context"
        assert "|" in text or "Feature" in text, "fees follow-up did not stay in comparison mode"
        return text[:220]

    run_case("fees_followup", fees_followup)

    def specific_card_followup():
        session = SessionMemory("t10")
        chat_flow.handle_preference_form(
            {
                "banking_type": "conventional",
                "use_case": "business_spending",
                "income_band": "200k_plus",
                "travel_frequency": "frequent",
                "tier_preference": "premium",
            },
            session,
        )
        text, _, _ = collect_text(chat_flow.build_crew_stream("Mastercard World", session))
        assert "Mastercard World" in text or len(text) > 80, "card details not returned"
        return text[:220]

    run_case("specific_card_followup", specific_card_followup)

    run_case(
        "how_to_apply",
        lambda: collect_text(chat_flow.build_crew_stream("How do I apply for a credit card?", SessionMemory("t11")))[0][:220],
    )
    run_case(
        "existing_cardholder",
        lambda: collect_text(chat_flow.build_crew_stream("I lost my card, what should I do?", SessionMemory("t12")))[0][:220],
    )
    run_case(
        "faq_interest_free",
        lambda: collect_text(chat_flow.build_crew_stream("Which cards offer interest-free period?", SessionMemory("t13")))[0][:220],
    )
    run_case(
        "off_topic",
        lambda: collect_text(chat_flow.build_crew_stream("Write me a poem about the moon", SessionMemory("t14")))[0][:160],
    )


if __name__ == "__main__":
    main()
