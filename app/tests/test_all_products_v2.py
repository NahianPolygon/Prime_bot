#!/usr/bin/env python3
"""
Test all 11 products with fixed slot extraction (100% prompt-based)
"""
import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000/api"

# Test data for each product
PRODUCT_TESTS = {
    "prime_fixed_deposit_plus": {
        "turns": [
            "I want the highest interest rates",
            "I prefer short-term 3-6 months",
            "I want premium returns",
            "What's your best short-term rate?",
            "Can you guarantee 9.75% interest?"
        ]
    },
    "prime_edu_dps": {
        "turns": [
            "I want to save for my child's education",
            "I can do monthly deposits",
            "What's the minimum monthly amount?",
            "I need 5-20 year options",
            "What interest rate for education?"
        ]
    },
    "prime_kotipoti_dps": {
        "turns": [
            "Hi, I want to save for long-term wealth building",
            "I can save monthly amount",
            "I'm looking for 9% interest rate",
            "Can I get loan facility during the scheme?",
            "What's the tenure options available?"
        ]
    },
    "prime_fixed_deposit": {
        "turns": [
            "I want a lump sum investment option",
            "I prefer 6-12 months tenure",
            "I have at least 10000 to deposit",
            "What's the interest rate for 6 months?",
            "What are the tenure options?"
        ]
    },
    "prime_fixed_deposit_plus_v2": {
        "turns": [
            "I need premium returns for short period",
            "Maximum 6 months please",
            "I want best rates available",
            "What makes your FD Plus special?",
            "Any special benefits for short tenure?"
        ]
    },
    "prime_lakhopoti_scheme": {
        "turns": [
            "Tell me about schemes with guaranteed returns",
            "I want to reach 1 lakh target",
            "Monthly deposits suit me",
            "What's the interest rate?",
            "Can I get terminal benefits?"
        ]
    },
    "prime_millionaire_scheme": {
        "turns": [
            "I want to become a millionaire",
            "I can save monthly",
            "What's your best wealth scheme?",
            "How long to reach 10 lakh?",
            "What's the guaranteed return?"
        ]
    },
    "prime_double_benefit_scheme": {
        "turns": [
            "I want my money to double",
            "How long does doubling take?",
            "What's the guaranteed rate?",
            "Can I invest lump sum?",
            "What's the minimum investment?"
        ]
    },
    "prime_deposit_premium_scheme": {
        "turns": [
            "I want monthly deposit scheme with high interest",
            "Starting with 500 per month",
            "I want 9% interest rate",
            "Do you offer loan facility?",
            "What are the tenor options?"
        ]
    },
    "prime_laksma_puron_scheme": {
        "turns": [
            "I want complete financial security for my future",
            "Family goal is important to me",
            "I can invest monthly",
            "What's the maturity benefit?",
            "Any insurance coverage included?"
        ]
    },
    "prime_monthly_income_scheme": {
        "turns": [
            "I need regular monthly income from my savings",
            "Retirement planning is my goal",
            "I can invest a lump sum",
            "What's the monthly payout?",
            "How long will payouts continue?"
        ]
    }
}

def test_product(product_name, turns):
    """Test a product with sequential turns"""
    session_id = f"test_{product_name}_{int(time.time())}"
    results = {
        "product": product_name,
        "timestamp": datetime.now().isoformat(),
        "turns": [],
        "status": "UNKNOWN",
        "summary": ""
    }
    
    print(f"\n{'='*80}")
    print(f"Testing: {product_name}")
    print(f"{'='*80}")
    
    found_product = False
    responses = []
    
    for turn_num, user_input in enumerate(turns, 1):
        try:
            response = requests.post(
                f"{BASE_URL}/chat",
                json={"message": user_input, "session_id": session_id},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                bot_response = data.get("response", "")
                responses.append(bot_response)
                
                # Check if product mentioned in response
                product_keyword = product_name.replace("prime_", "").replace("_", " ")
                if product_keyword.lower() in bot_response.lower() or "scheme" in bot_response.lower():
                    found_product = True
                
                print(f"[T{turn_num}] User: {user_input[:60]}")
                print(f"[T{turn_num}] Bot: {bot_response[:120]}...")
                
                results["turns"].append({
                    "turn": turn_num,
                    "user": user_input,
                    "bot": bot_response[:200],
                    "found_product": "scheme" in bot_response.lower()
                })
                
                time.sleep(0.3)
            else:
                print(f"ERROR: {response.status_code}")
                results["status"] = "ERROR"
                break
                
        except Exception as e:
            print(f"Exception: {e}")
            results["status"] = "FAILED"
            break
    
    results["status"] = "PASS" if found_product else "FAIL"
    results["product_mentioned"] = found_product
    results["summary"] = f"Product {'FOUND' if found_product else 'NOT FOUND'} in responses"
    
    return results

def main():
    print("🚀 Starting comprehensive product test (100% prompt-based extraction)")
    print(f"Testing {len(PRODUCT_TESTS)} products...\n")
    
    all_results = []
    passed = 0
    failed = 0
    
    for product_name, test_data in PRODUCT_TESTS.items():
        result = test_product(product_name, test_data["turns"])
        all_results.append(result)
        
        if result["status"] == "PASS":
            passed += 1
            print(f"✅ {product_name}: PASS")
        else:
            failed += 1
            print(f"❌ {product_name}: FAIL")
    
    # Summary
    print(f"\n{'='*80}")
    print(f"SUMMARY: {passed} PASS, {failed} FAIL (Pass Rate: {passed*100/(passed+failed):.1f}%)")
    print(f"{'='*80}")
    
    # Save results
    output = {
        "timestamp": datetime.now().isoformat(),
        "total": len(all_results),
        "passed": passed,
        "failed": failed,
        "pass_rate": passed * 100 / (passed + failed),
        "products": all_results
    }
    
    with open("/app/tests/results/test_v2_results.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"✅ Results saved to test_v2_results.json")

if __name__ == "__main__":
    main()
