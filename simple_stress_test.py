#!/usr/bin/env python3
"""
Simple Sequential Stress Test
Tests if the bot recommends exact products by their IDs
"""

import asyncio
import httpx
import json
import time
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"
TIMEOUT = 30.0

# All products from knowledge base
PRODUCTS = {
    "conventional_credit": [
        "jcb_gold_credit_card",
        "jcb_platinum_credit_card",
        "mastercard_platinum_credit_card",
        "mastercard_world_credit_card",
        "visa_gold_credit_card",
        "visa_platinum_credit_card",
    ],
    "conventional_savings": [
        "prime_50_plus_savings_account",
        "prime_atlas_fc_account",
        "prime_current_account",
        "prime_first_account",
        "prime_freelancer_account",
        "prime_one_savings_account",
        "prime_personal_retail_account",
        "prime_porijon_savings_account",
        "prime_savings_account",
        "prime_teachers_account",
        "prime_youth_account",
        "resident_foreign_currency_deposit_account",
    ],
    "conventional_schemes": [
        "prime_deposit_premium_scheme",
        "prime_double_benefit_scheme",
        "prime_edu_dps",
        "prime_fixed_deposit",
        "prime_fixed_deposit_plus",
        "prime_i_first_fd",
        "prime_kotipoti_dps",
        "prime_lakhopoti_scheme",
        "prime_laksma_puron_scheme",
        "prime_millionaire_scheme",
        "prime_monthly_income_scheme",
        "prime_profit_first_td",
    ],
    "islami_credit": [
        "visa_hasanah_gold_credit_card",
        "visa_hasanah_platinum_credit_card",
    ],
    "islami_savings": [
        "prime_hasanah_50plus_savings_account",
        "prime_hasanah_atlas_fc_account",
        "prime_hasanah_current_account",
        "prime_hasanah_first_account",
        "prime_hasanah_freelancer_account",
        "prime_hasanah_nfcd_account",
        "prime_hasanah_one_savings_account",
        "prime_hasanah_personal_retail_account",
        "prime_hasanah_porijon_savings_account",
        "prime_hasanah_rfcd_savings_account",
        "prime_hasanah_savings_account",
        "prime_hasanah_teachers_account",
        "prime_hasanah_womens_savings_account",
        "prime_hasanah_youth_account",
        "sadaqah_jariyah_account",
    ],
    "islami_schemes": [
        "prime_hasanah_deposit_premium_scheme",
        "prime_hasanah_edu_dps",
        "prime_hasanah_hajj_scheme",
        "prime_hasanah_laksma_puron_dps",
        "prime_hasanah_monthly_income_scheme",
        "prime_hasanah_term_deposit",
        "prime_hasanah_term_deposit_plus",
    ],
}

# Get all product IDs
ALL_PRODUCTS = []
for category in PRODUCTS.values():
    ALL_PRODUCTS.extend(category)

# Test cases with expected products
TEST_CASES = [
    {
        "query": "Tell me about DPS schemes",
        "expected": ["prime_kotipoti_dps", "prime_lakhopoti_scheme", "prime_edu_dps"],
        "category": "DPS Schemes"
    },
    {
        "query": "I want a fixed deposit",
        "expected": ["prime_fixed_deposit", "prime_fixed_deposit_plus"],
        "category": "Fixed Deposits"
    },
    {
        "query": "What millionaire scheme do you have?",
        "expected": ["prime_millionaire_scheme"],
        "category": "Millionaire Scheme"
    },
    {
        "query": "I'm a student, what account should I open?",
        "expected": ["prime_youth_account"],
        "category": "Youth Account"
    },
    {
        "query": "I'm 50+ years old, what savings account?",
        "expected": ["prime_50_plus_savings_account"],
        "category": "50+ Savings"
    },
    {
        "query": "I'm a freelancer, what account?",
        "expected": ["prime_freelancer_account"],
        "category": "Freelancer Account"
    },
    {
        "query": "I want Islamic banking products",
        "expected": ["prime_hasanah_savings_account", "prime_hasanah_current_account"],
        "category": "Islamic Banking"
    },
    {
        "query": "Tell me about Hajj savings scheme",
        "expected": ["prime_hasanah_hajj_scheme"],
        "category": "Hajj Scheme"
    },
    {
        "query": "What credit cards do you have?",
        "expected": ["visa_gold_credit_card", "mastercard_platinum_credit_card", "jcb_platinum_credit_card"],
        "category": "Credit Cards"
    },
    {
        "query": "I need Islamic credit card",
        "expected": ["visa_hasanah_gold_credit_card", "visa_hasanah_platinum_credit_card"],
        "category": "Islamic Credit Cards"
    },
]

class SimpleStressTest:
    def __init__(self):
        self.results = []
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.partial = 0
    
    async def test_query(self, query: str, expected_products: list, category: str):
        """Test a single query"""
        session_id = f"test_{self.total}_{int(time.time() * 1000)}"
        self.total += 1
        
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                start = time.time()
                response = await client.post(
                    f"{BASE_URL}/api/chat",
                    json={"message": query, "session_id": session_id},
                )
                elapsed = time.time() - start
                
                if response.status_code != 200:
                    logger.error(f"❌ {category}: HTTP {response.status_code}")
                    self.failed += 1
                    return
                
                data = response.json()
                bot_response = data.get("response", "").lower()
                
                # Check which products were mentioned
                found = []
                for product in expected_products:
                    # Check if product name is in response (with underscores or spaces)
                    product_normalized = product.lower().replace("_", " ")
                    if product.lower() in bot_response or product_normalized in bot_response:
                        found.append(product)
                
                # Determine result
                if len(found) == len(expected_products):
                    logger.info(f"✅ {category}")
                    logger.info(f"   Query: {query}")
                    logger.info(f"   Found all {len(found)} products: {', '.join(found)}")
                    logger.info(f"   Time: {elapsed:.2f}s\n")
                    self.passed += 1
                elif len(found) > 0:
                    logger.warning(f"⚠️  {category} (PARTIAL)")
                    logger.warning(f"   Query: {query}")
                    logger.warning(f"   Expected: {', '.join(expected_products)}")
                    logger.warning(f"   Found: {', '.join(found)} ({len(found)}/{len(expected_products)})")
                    logger.warning(f"   Time: {elapsed:.2f}s")
                    logger.warning(f"   Response: {bot_response[:200]}...\n")
                    self.partial += 1
                else:
                    logger.error(f"❌ {category} (FAILED)")
                    logger.error(f"   Query: {query}")
                    logger.error(f"   Expected: {', '.join(expected_products)}")
                    logger.error(f"   Found: NONE")
                    logger.error(f"   Time: {elapsed:.2f}s")
                    logger.error(f"   Response: {bot_response[:200]}...\n")
                    self.failed += 1
                
                self.results.append({
                    "category": category,
                    "query": query,
                    "expected": expected_products,
                    "found": found,
                    "status": "passed" if len(found) == len(expected_products) else ("partial" if len(found) > 0 else "failed"),
                    "time": elapsed
                })
                
                await asyncio.sleep(0.2)
        
        except asyncio.TimeoutError:
            logger.error(f"⏱️  {category}: TIMEOUT (>{TIMEOUT}s)")
            self.failed += 1
        except Exception as e:
            logger.error(f"❌ {category}: {str(e)}")
            self.failed += 1
    
    async def run_all(self):
        """Run all tests"""
        logger.info("="*80)
        logger.info("SEQUENTIAL PRODUCT RECOMMENDATION TEST")
        logger.info("="*80)
        logger.info(f"Testing if bot recommends exact product IDs\n")
        
        for test in TEST_CASES:
            await self.test_query(test["query"], test["expected"], test["category"])
        
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        logger.info("\n" + "="*80)
        logger.info("TEST SUMMARY")
        logger.info("="*80)
        
        logger.info(f"\nTotal Tests: {self.total}")
        logger.info(f"✅ Passed (all products found): {self.passed}")
        logger.info(f"⚠️  Partial (some products found): {self.partial}")
        logger.info(f"❌ Failed (no products found): {self.failed}")
        
        pass_rate = (self.passed / self.total * 100) if self.total > 0 else 0
        logger.info(f"\nPass Rate: {pass_rate:.1f}%")
        
        # Details
        logger.info("\nDetailed Results:")
        for result in self.results:
            status_icon = "✅" if result["status"] == "passed" else ("⚠️ " if result["status"] == "partial" else "❌")
            logger.info(f"{status_icon} {result['category']}: {result['status'].upper()}")
            if result["status"] != "passed":
                logger.info(f"   Expected: {', '.join(result['expected'])}")
                logger.info(f"   Found: {', '.join(result['found']) if result['found'] else 'NONE'}")

async def main():
    logger.info("Starting Sequential Product Recommendation Test\n")
    logger.info(f"Target: {BASE_URL}")
    logger.info(f"Start Time: {datetime.now().isoformat()}\n")
    
    tester = SimpleStressTest()
    
    try:
        await tester.run_all()
    except KeyboardInterrupt:
        logger.info("\n⚠️  Test interrupted")
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
    finally:
        logger.info(f"\nEnd Time: {datetime.now().isoformat()}")

if __name__ == "__main__":
    asyncio.run(main())
