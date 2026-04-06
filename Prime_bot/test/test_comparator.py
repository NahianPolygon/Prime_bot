import argparse
import csv
import json
import os
import re
import time
from datetime import datetime

import requests

API_BASE = os.getenv("API_BASE", "http://localhost:8000")
CSV_FILE = os.getenv("CSV_FILE", "test_results.csv")
SESSION_FILE = os.getenv("SESSION_FILE", "test_sessions.json")

SCENARIOS = {
    "S01_visa_gold_vs_platinum": [
        "Compare Visa Gold and Visa Platinum credit cards",
        "I earn 150k per month and love dining out. Which one is better for me?",
        "What about the insurance coverage difference between them?",
    ],
    "S02_conventional_vs_islami_platinum": [
        "Compare Visa Platinum and Visa Hasanah Platinum",
        "I want shariah compliant banking. Is Hasanah Platinum good for travel?",
        "Which one has better dining benefits?",
    ],
    "S03_two_mastercards": [
        "Compare the two master cards prime bank offers",
        "If I earn 500k per month and I want a premium lifestyle which one will be the best for me?",
    ],
    "S04_gold_vs_hasanah_platinum": [
        "Compare Visa Gold with Visa Hasanah Platinum",
        "I am a business owner earning 300k monthly. Which suits me?",
    ],
    "S05_all_platinum_cards": [
        "Compare all platinum tier credit cards",
        "Which platinum card has the highest credit limit?",
    ],
    "S06_travel_focused": [
        "Compare cards best for international travel",
        "I travel 6 times a year internationally. Which card gives best lounge access?",
        "Does the Islamic card also offer LoungeKey?",
    ],
    "S07_dining_focused": [
        "Which credit cards have BOGO dining benefits? Compare them",
        "I dine at luxury restaurants every week. Which card saves me the most?",
    ],
    "S08_fee_comparison": [
        "Compare annual fees of Visa Gold, Visa Platinum and Visa Hasanah Platinum",
        "Which card is easiest to get fee waiver on?",
    ],
    "S09_insurance_comparison": [
        "Compare insurance benefits across all credit cards",
        "My family depends on me financially. Which card offers best protection?",
    ],
    "S10_emi_comparison": [
        "Compare EMI or installment benefits of Visa Gold vs Visa Platinum",
        "I want to buy electronics worth 5 lakh on EMI. Which card is better?",
    ],
    "S11_eligibility_after_compare": [
        "Compare Visa Gold and Visa Hasanah Platinum",
        "Am I eligible for Visa Hasanah Platinum if I earn 200k per month?",
    ],
    "S12_vague_compare": [
        "Compare your best cards",
        "Which one has the most rewards?",
        "Tell me more about that card",
    ],
    "S13_income_based_recommendation": [
        "Compare cards suitable for someone earning 50k per month",
        "What if my income increases to 200k? Which card should I upgrade to?",
    ],
    "S14_cross_network_compare": [
        "Compare Visa cards with Mastercard options",
        "Which network gives better international acceptance?",
    ],
    "S15_islamic_only_compare": [
        "Compare all Islamic credit cards you have",
        "Which Islamic card is best for a business owner?",
    ],
}

CSV_HEADERS = [
    "scenario_id",
    "session_id",
    "turn",
    "timestamp",
    "user_message",
    "bot_response",
    "response_chars",
    "latency_ms",
    "has_table",
    "table_count",
    "has_internal_codes",
    "internal_codes_found",
    "has_extra_separators",
    "extra_separator_count",
    "has_required_rows",
    "missing_rows",
    "has_best_for",
    "has_eligibility_cta",
    "has_na_values",
    "http_status",
    "error",
]

REQUIRED_TABLE_ROWS = [
    "credit limit",
    "annual fee",
    "fee waiver",
    "reward points",
    "interest-free period",
    "insurance",
    "key benefits",
    "banking type",
]


def analyze_response(text):
    metrics = {}
    metrics["response_chars"] = len(text)

    table_matches = re.findall(r"\|.+\|", text)
    data_rows = [r for r in table_matches if not re.match(r"^\|[\s\-:|]+\|$", r.strip())]
    metrics["has_table"] = len(data_rows) > 0
    metrics["table_count"] = len(data_rows)

    internal_pattern = re.compile(r"\b(?:ISLAMI_CARD|CARD)_\d+\b")
    found_codes = internal_pattern.findall(text)
    metrics["has_internal_codes"] = len(found_codes) > 0
    metrics["internal_codes_found"] = "|".join(found_codes) if found_codes else ""

    extra_seps = 0
    lines = text.split("\n")
    sep_count = 0
    in_table = False
    for line in lines:
        stripped = line.strip()
        is_pipe = stripped.startswith("|") and stripped.endswith("|") and len(stripped) > 2
        is_sep = bool(re.match(r"^\|[\s\-:|]+\|$", stripped))
        if is_pipe or is_sep:
            if not in_table:
                in_table = True
                sep_count = 0
            if is_sep:
                sep_count += 1
                if sep_count > 1:
                    extra_seps += 1
        else:
            if in_table and stripped == "":
                continue
            in_table = False
            sep_count = 0

    metrics["has_extra_separators"] = extra_seps > 0
    metrics["extra_separator_count"] = extra_seps

    text_lower = text.lower()
    missing = []
    for row_name in REQUIRED_TABLE_ROWS:
        if row_name not in text_lower:
            missing.append(row_name)

    metrics["has_required_rows"] = len(missing) == 0
    metrics["missing_rows"] = "|".join(missing) if missing else ""
    metrics["has_best_for"] = "best for" in text_lower
    metrics["has_eligibility_cta"] = "eligibility" in text_lower
    metrics["has_na_values"] = "n/a" in text_lower
    return metrics


def load_sessions():
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_sessions(sessions):
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(sessions, f, indent=2)


def load_existing_results():
    rows = []
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
    return rows


def save_results(rows):
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def append_result_row(row):
    file_exists = os.path.exists(CSV_FILE)
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        if not file_exists or os.path.getsize(CSV_FILE) == 0:
            writer.writeheader()
        writer.writerow(row)


def send_message(message, session_id=None):
    payload = {"message": message}
    if session_id:
        payload["session_id"] = session_id

    start = time.perf_counter()
    try:
        resp = requests.post(f"{API_BASE}/chat", json=payload, timeout=300)
        latency = round((time.perf_counter() - start) * 1000, 2)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "response": data.get("response", ""),
                "session_id": data.get("session_id", ""),
                "http_status": 200,
                "latency_ms": latency,
                "error": "",
            }

        return {
            "response": "",
            "session_id": session_id or "",
            "http_status": resp.status_code,
            "latency_ms": latency,
            "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
        }
    except Exception as e:
        latency = round((time.perf_counter() - start) * 1000, 2)
        return {
            "response": "",
            "session_id": session_id or "",
            "http_status": 0,
            "latency_ms": latency,
            "error": str(e),
        }


def get_max_turn_completed(existing_rows, scenario_id):
    max_turn = 0
    for row in existing_rows:
        if row.get("scenario_id") == scenario_id:
            try:
                t = int(row["turn"])
                if t > max_turn:
                    max_turn = t
            except (ValueError, KeyError):
                pass
    return max_turn


def format_progress(current, total, width=28):
    if total <= 0:
        return "[" + ("-" * width) + "]   0.0%"
    ratio = current / total
    filled = int(width * ratio)
    bar = "#" * filled + "-" * (width - filled)
    return f"[{bar}] {ratio * 100:5.1f}%"


def run_turn(turn_number):
    sessions = load_sessions()
    existing_rows = load_existing_results()
    new_rows = []

    total = len(SCENARIOS)
    completed = 0

    for scenario_id, turns in SCENARIOS.items():
        completed += 1
        turn_index = turn_number - 1
        progress = format_progress(completed, total)

        if turn_index >= len(turns):
            print(f"{progress} [{completed}/{total}] {scenario_id}: No turn {turn_number} defined, skipping")
            continue

        already_done = get_max_turn_completed(existing_rows, scenario_id)
        if already_done >= turn_number:
            print(f"{progress} [{completed}/{total}] {scenario_id}: Turn {turn_number} already done, skipping")
            continue

        if turn_number > 1 and already_done < turn_number - 1:
            print(f"{progress} [{completed}/{total}] {scenario_id}: Turn {turn_number - 1} not done yet, skipping")
            continue

        session_id = sessions.get(scenario_id)
        message = turns[turn_index]
        print(f"{progress} [{completed}/{total}] {scenario_id} turn {turn_number}: {message[:60]}...")

        result = send_message(message, session_id)
        if result["session_id"]:
            sessions[scenario_id] = result["session_id"]

        metrics = analyze_response(result["response"])
        row = {
            "scenario_id": scenario_id,
            "session_id": result["session_id"],
            "turn": turn_number,
            "timestamp": datetime.utcnow().isoformat(),
            "user_message": message,
            "bot_response": result["response"].replace("\n", "\\n"),
            "response_chars": metrics["response_chars"],
            "latency_ms": result["latency_ms"],
            "has_table": metrics["has_table"],
            "table_count": metrics["table_count"],
            "has_internal_codes": metrics["has_internal_codes"],
            "internal_codes_found": metrics["internal_codes_found"],
            "has_extra_separators": metrics["has_extra_separators"],
            "extra_separator_count": metrics["extra_separator_count"],
            "has_required_rows": metrics["has_required_rows"],
            "missing_rows": metrics["missing_rows"],
            "has_best_for": metrics["has_best_for"],
            "has_eligibility_cta": metrics["has_eligibility_cta"],
            "has_na_values": metrics["has_na_values"],
            "http_status": result["http_status"],
            "error": result["error"],
        }
        new_rows.append(row)
        existing_rows.append(row)
        append_result_row(row)
        save_sessions(sessions)

        print(
            f"    -> {metrics['response_chars']} chars, {result['latency_ms']}ms, "
            f"table={metrics['has_table']}, codes={metrics['has_internal_codes']}, "
            f"extra_sep={metrics['extra_separator_count']}, missing={metrics['missing_rows']}"
        )
        time.sleep(1)

    all_rows = load_existing_results()

    print(f"\nDone. {len(new_rows)} new results added. Total rows: {len(all_rows)}")
    print(f"Results: {CSV_FILE}")
    print(f"Sessions: {SESSION_FILE}")

    print_summary(new_rows, turn_number)


def print_summary(rows, turn_number):
    if not rows:
        return

    print(f"\n{'=' * 70}")
    print(f"TURN {turn_number} SUMMARY")
    print(f"{'=' * 70}")

    total = len(rows)
    tables = sum(1 for r in rows if str(r["has_table"]).lower() == "true")
    codes = sum(1 for r in rows if str(r["has_internal_codes"]).lower() == "true")
    extra_seps = sum(1 for r in rows if str(r["has_extra_separators"]).lower() == "true")
    required = sum(1 for r in rows if str(r["has_required_rows"]).lower() == "true")
    best_for = sum(1 for r in rows if str(r["has_best_for"]).lower() == "true")
    cta = sum(1 for r in rows if str(r["has_eligibility_cta"]).lower() == "true")
    errors = sum(1 for r in rows if r["error"])
    avg_latency = sum(float(r["latency_ms"]) for r in rows) / total

    print(f"Total scenarios run:     {total}")
    print(f"Has table:               {tables}/{total}")
    print(f"Has internal codes:      {codes}/{total}  {'FAIL' if codes > 0 else 'PASS'}")
    print(f"Has extra separators:    {extra_seps}/{total}")
    print(f"Has all required rows:   {required}/{total}")
    print(f"Has 'Best For' section:  {best_for}/{total}")
    print(f"Has eligibility CTA:     {cta}/{total}")
    print(f"Errors:                  {errors}/{total}")
    print(f"Avg latency:             {avg_latency:.0f}ms")

    if codes > 0:
        print("\nINTERNAL CODES LEAKED:")
        for r in rows:
            if str(r["has_internal_codes"]).lower() == "true":
                print(f"  {r['scenario_id']}: {r['internal_codes_found']}")

    missing_scenarios = [r for r in rows if r["missing_rows"]]
    if missing_scenarios:
        print("\nMISSING TABLE ROWS:")
        for r in missing_scenarios:
            print(f"  {r['scenario_id']}: {r['missing_rows']}")


def reset():
    if os.path.exists(CSV_FILE):
        os.remove(CSV_FILE)
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)
    print("Reset complete. Cleared CSV and session files.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test comparator responses")
    parser.add_argument("--turn", type=int, required=False, help="Turn number to run (1, 2, 3...)")
    parser.add_argument("--reset", action="store_true", help="Clear all test data")
    parser.add_argument("--summary", action="store_true", help="Print summary of existing results")
    args = parser.parse_args()

    if args.reset:
        reset()
    elif args.summary:
        rows = load_existing_results()
        if not rows:
            print("No results found.")
        else:
            turns = set(r["turn"] for r in rows)
            for t in sorted(turns, key=lambda x: int(x)):
                turn_rows = [r for r in rows if r["turn"] == str(t)]
                print_summary(turn_rows, t)
    elif args.turn:
        run_turn(args.turn)
    else:
        print("Usage:")
        print("  python test_comparator.py --turn 1     Run turn 1 of all scenarios")
        print("  python test_comparator.py --turn 2     Run turn 2 (follow-ups)")
        print("  python test_comparator.py --turn 3     Run turn 3 (second follow-ups)")
        print("  python test_comparator.py --summary    Print summary of all results")
        print("  python test_comparator.py --reset      Clear all test data")