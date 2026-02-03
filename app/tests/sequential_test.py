#!/usr/bin/env python3
"""
Sequential Product Test - Deposit Schemes
Tests if the bot can guide to specific products through sequential conversations
"""

import asyncio
import httpx
import json
import time
from datetime import datetime
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"
TIMEOUT = 30.0
RESULTS_DIR = Path("/app/tests/results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Sequential conversation test cases based on product features
TEST_CASES = [
    {
        "product": "prime_kotipoti_dps",
        "tagline": "Make the Right Choice Along the Way",
        "key_features": ["9% interest", "5-15 years", "monthly installment", "loan facility"],
        "conversation": [
            "Hi, I want to save for long-term wealth building",
            "I can save monthly amount",
            "I'm looking for 9% interest rate",
            "Can I get loan facility during the scheme?",
            "What's the tenure options available?",
        ],
        "expected_mentions": ["kotipoti", "9%", "5-15 years", "loan facility"]
    },
    {
        "product": "prime_lakhopoti_scheme",
        "tagline": "Toward Big Changes",
        "key_features": ["1 lakh guaranteed", "3-15 years", "terminal benefit", "6-7% interest"],
        "conversation": [
            "I want to guarantee 1 lakh at maturity",
            "I can do monthly deposits",
            "What schemes give terminal benefit?",
            "Can I choose 3-5 year tenure?",
            "How much monthly should I deposit?",
        ],
        "expected_mentions": ["lakhopoti", "1 lakh", "terminal benefit", "guaranteed"]
    },
    {
        "product": "prime_i_first_fd",
        "tagline": "Start with a Win - Earn Interest on Day One",
        "key_features": ["interest on day 1", "1 lakh minimum", "12 month", "principal protected"],
        "conversation": [
            "I want interest paid immediately when I open the account",
            "I have 1 lakh to invest",
            "I prefer 12 months tenure",
            "My principal should be protected",
            "Is interest credited on opening day?",
        ],
        "expected_mentions": ["i-first", "day one", "interest paid", "advance interest"]
    },
    {
        "product": "prime_fixed_deposit",
        "tagline": "Saving Today for a Comfortable Tomorrow",
        "key_features": ["lump sum", "1-36 months", "7-8% interest", "10000 minimum"],
        "conversation": [
            "I want a lump sum investment option",
            "I prefer 6-12 months tenure",
            "I have at least 10000 to deposit",
            "What's the interest rate for 6 months?",
            "What are the tenure options?",
        ],
        "expected_mentions": ["fixed deposit", "lump sum", "1-36 months", "flexible tenors"]
    },
    {
        "product": "prime_fixed_deposit_plus",
        "tagline": "Premium Returns for Premium Savers",
        "key_features": ["9.75-10% interest", "91-181 days", "short term", "premium returns"],
        "conversation": [
            "I want the highest interest rates",
            "I prefer short-term 3-6 months",
            "I want premium returns",
            "What's your best short-term rate?",
            "Can you guarantee 9.75% interest?",
        ],
        "expected_mentions": ["fd plus", "9.75%", "10%", "premium", "short-term"]
    },
    {
        "product": "prime_edu_dps",
        "tagline": "Invest for Education, Secure the Future",
        "key_features": ["child education", "9% interest", "5-20 years", "500 minimum"],
        "conversation": [
            "I want to save for my child's education",
            "I can do monthly deposits",
            "What's the minimum monthly amount?",
            "I need 5-20 year options",
            "What interest rate for education?",
        ],
        "expected_mentions": ["edu dps", "education", "child", "9%", "5-20 years"]
    },
    {
        "product": "prime_double_benefit_scheme",
        "tagline": "Twice the Drive, Twice the Reward",
        "key_features": ["money doubles", "7 years 11 months", "9.25% interest", "lump sum"],
        "conversation": [
            "I want my money to double",
            "How long does it take to double?",
            "I can do lump sum investment",
            "What interest rate guarantees doubling?",
            "Can I invest 10000 or more?",
        ],
        "expected_mentions": ["double benefit", "doubles", "7 years 11 months", "9.25%"]
    },
    {
        "product": "prime_deposit_premium_scheme",
        "tagline": "Premium Savings with Premium Returns",
        "key_features": ["9% interest", "500 minimum", "3-10 years", "loan facility"],
        "conversation": [
            "I want monthly deposit scheme with high interest",
            "Starting with 500 per month",
            "I want 9% interest rate",
            "Do you offer loan facility?",
            "What are the tenor options?",
        ],
        "expected_mentions": ["deposit premium", "9%", "monthly", "loan facility", "3-10 years"]
    },
    {
        "product": "prime_laksma_puron_scheme",
        "tagline": "Who Says Sky is the Limit? Set Your Own Limit",
        "key_features": ["custom goal", "6% interest", "3-5 years", "flexible amount"],
        "conversation": [
            "I have a custom financial goal in mind",
            "I want to set my own target amount",
            "I prefer 3-5 year tenure",
            "What interest rate for this scheme?",
            "How do I calculate monthly deposit?",
        ],
        "expected_mentions": ["laksma puron", "custom goal", "6%", "set your own", "3-5 years"]
    },
    {
        "product": "prime_millionaire_scheme",
        "tagline": "My First Million Made the Easiest",
        "key_features": ["10 lakh target", "fixed monthly", "6-7% interest", "5-12 years"],
        "conversation": [
            "I want to become a millionaire",
            "I want fixed monthly payments for budgeting",
            "What's the target amount?",
            "What monthly installment for 5 years?",
            "What interest rate is offered?",
        ],
        "expected_mentions": ["millionaire", "10 lakh", "million", "fixed monthly", "6-7%"]
    },
    {
        "product": "prime_monthly_income_scheme",
        "tagline": "Invest & Earn Extra",
        "key_features": ["monthly income", "100000 minimum", "principal protected", "retirees"],
        "conversation": [
            "I need regular monthly income from my investment",
            "I want my principal protected",
            "I have 100000 to invest",
            "Is this suitable for retirees?",
            "Can I get monthly payouts?",
        ],
        "expected_mentions": ["monthly income", "mis", "regular income", "principal", "100000"]
    },
]

class SequentialTest:
    def __init__(self):
        self.results = []
        self.session_mapping = {}  # product -> session_id
    
    async def test_product(self, test_case):
        """Test a single product through sequential conversation"""
        product = test_case["product"]
        conversation = test_case["conversation"]
        expected_mentions = test_case["expected_mentions"]
        
        logger.info(f"\n{'='*80}")
        logger.info(f"Testing: {product}")
        logger.info(f"{'='*80}")
        logger.info(f"Key features to match: {', '.join(expected_mentions)}\n")
        
        session_id = f"product_test_{product}_{int(time.time() * 1000)}"
        self.session_mapping[product] = session_id
        
        conversation_log = []
        all_responses = []
        product_found = False
        found_features = []
        
        for turn, user_message in enumerate(conversation, 1):
            logger.info(f"Turn {turn}:")
            logger.info(f"  User: {user_message}")
            
            try:
                async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                    start = time.time()
                    response = await client.post(
                        f"{BASE_URL}/api/chat",
                        json={"message": user_message, "session_id": session_id},
                    )
                    elapsed = time.time() - start
                    
                    if response.status_code != 200:
                        logger.error(f"  ❌ HTTP {response.status_code}")
                        break
                    
                    data = response.json()
                    bot_response = data.get("response", "")
                    bot_response_lower = bot_response.lower()
                    
                    logger.info(f"  Bot: {bot_response[:150]}...")
                    logger.info(f"  Time: {elapsed:.2f}s")
                    
                    conversation_log.append({
                        "turn": turn,
                        "user": user_message,
                        "bot": bot_response,
                        "time": elapsed
                    })
                    all_responses.append(bot_response_lower)
                    
                    # Check for product mentions in this turn
                    for feature in expected_mentions:
                        if feature.lower() in bot_response_lower:
                            if feature not in found_features:
                                found_features.append(feature)
                                logger.info(f"  ✅ Found: {feature}")
                    
                    await asyncio.sleep(0.3)
                
            except Exception as e:
                logger.error(f"  ❌ Error: {str(e)}")
                break
        
        # Compile all responses to check for product mention
        full_conversation = " ".join(all_responses)
        if product.lower() in full_conversation or product.replace("_", " ").lower() in full_conversation:
            product_found = True
        
        # Determine result
        match_ratio = len(found_features) / len(expected_mentions) if expected_mentions else 0
        status = "PASS" if match_ratio >= 0.7 else ("PARTIAL" if match_ratio > 0 else "FAIL")
        
        logger.info(f"\nResult: {status}")
        logger.info(f"  Found {len(found_features)}/{len(expected_mentions)} features")
        logger.info(f"  Product ID found: {product_found}")
        logger.info(f"  Accuracy: {match_ratio*100:.0f}%")
        
        result = {
            "product": product,
            "status": status,
            "product_found": product_found,
            "features_found": found_features,
            "features_total": len(expected_mentions),
            "accuracy": match_ratio,
            "conversation": conversation_log,
        }
        
        self.results.append(result)
        
        # Save individual conversation log
        self.save_conversation_log(product, conversation_log, result)
        
        return result
    
    def save_conversation_log(self, product, conversation, result):
        """Save individual conversation log"""
        log_file = RESULTS_DIR / f"{product}_conversation.json"
        
        with open(log_file, 'w') as f:
            json.dump({
                "product": product,
                "timestamp": datetime.now().isoformat(),
                "status": result["status"],
                "product_found": result["product_found"],
                "features_found": result["features_found"],
                "accuracy": result["accuracy"],
                "conversation": conversation,
            }, f, indent=2)
        
        logger.info(f"  Saved: {log_file}")
    
    async def run_all_tests(self):
        """Run all product tests"""
        logger.info("="*80)
        logger.info("SEQUENTIAL PRODUCT GUIDANCE TEST")
        logger.info("="*80)
        logger.info(f"Testing {len(TEST_CASES)} deposit scheme products\n")
        
        for test_case in TEST_CASES:
            await self.test_product(test_case)
            await asyncio.sleep(1)
        
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        logger.info("\n" + "="*80)
        logger.info("TEST SUMMARY")
        logger.info("="*80)
        
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        partial = sum(1 for r in self.results if r["status"] == "PARTIAL")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        
        logger.info(f"\nTotal Tests: {len(self.results)}")
        logger.info(f"✅ Passed: {passed}")
        logger.info(f"⚠️  Partial: {partial}")
        logger.info(f"❌ Failed: {failed}")
        
        pass_rate = (passed / len(self.results) * 100) if self.results else 0
        logger.info(f"\nPass Rate: {pass_rate:.1f}%")
        
        # Detailed results
        logger.info("\n" + "="*80)
        logger.info("DETAILED RESULTS")
        logger.info("="*80)
        
        for result in self.results:
            status_icon = "✅" if result["status"] == "PASS" else ("⚠️ " if result["status"] == "PARTIAL" else "❌")
            logger.info(f"\n{status_icon} {result['product']}: {result['status']}")
            logger.info(f"   Product ID found: {result['product_found']}")
            logger.info(f"   Features found: {len(result['features_found'])}/{result['features_total']}")
            logger.info(f"   Accuracy: {result['accuracy']*100:.0f}%")
            if result['features_found']:
                logger.info(f"   Found: {', '.join(result['features_found'])}")
        
        # Save summary
        self.save_summary()
    
    def save_summary(self):
        """Save overall summary"""
        summary_file = RESULTS_DIR / "summary.json"
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(self.results),
            "passed": sum(1 for r in self.results if r["status"] == "PASS"),
            "partial": sum(1 for r in self.results if r["status"] == "PARTIAL"),
            "failed": sum(1 for r in self.results if r["status"] == "FAIL"),
            "results": [
                {
                    "product": r["product"],
                    "status": r["status"],
                    "product_found": r["product_found"],
                    "features_found": r["features_found"],
                    "accuracy": r["accuracy"],
                }
                for r in self.results
            ]
        }
        
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"\n✅ Summary saved to: {summary_file}")
        logger.info(f"✅ Conversation logs saved to: {RESULTS_DIR}")

async def main():
    logger.info("Starting Sequential Product Guidance Test\n")
    logger.info(f"Target: {BASE_URL}")
    logger.info(f"Start Time: {datetime.now().isoformat()}\n")
    
    tester = SequentialTest()
    
    try:
        await tester.run_all_tests()
    except KeyboardInterrupt:
        logger.info("\n⚠️  Test interrupted")
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
    finally:
        logger.info(f"\nEnd Time: {datetime.now().isoformat()}")

if __name__ == "__main__":
    asyncio.run(main())
