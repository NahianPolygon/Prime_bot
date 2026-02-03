#!/usr/bin/env python3
"""
Prime Bank Chatbot Comprehensive Stress Test
Focuses on product retrieval and greetings
"""

import asyncio
import httpx
import json
import time
import random
import statistics
from dataclasses import dataclass
from typing import List, Dict, Tuple
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"
TIMEOUT = 30.0

@dataclass
class TestResult:
    test_name: str
    status: str  # "passed", "failed", "timeout"
    response_time: float
    status_code: int = None
    error_message: str = None
    response_text: str = None

class ProductDatabase:
    """Database of actual products from knowledge base"""
    
    PRODUCTS = {
        "conventional": {
            "credit": [
                "jcb_gold_credit_card",
                "jcb_platinum_credit_card",
                "mastercard_platinum_credit_card",
                "mastercard_world_credit_card",
                "visa_gold_credit_card",
                "visa_platinum_credit_card",
            ],
            "save": {
                "accounts": [
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
                "schemes": [
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
                ]
            }
        },
        "islami": {
            "credit": [
                "visa_hasanah_gold_credit_card",
                "visa_hasanah_platinum_credit_card",
            ],
            "save": {
                "accounts": [
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
                "schemes": [
                    "prime_hasanah_deposit_premium_scheme",
                    "prime_hasanah_edu_dps",
                    "prime_hasanah_hajj_scheme",
                    "prime_hasanah_laksma_puron_dps",
                    "prime_hasanah_monthly_income_scheme",
                    "prime_hasanah_term_deposit",
                    "prime_hasanah_term_deposit_plus",
                ]
            }
        }
    }
    
    @staticmethod
    def get_all_products():
        """Get all products for testing"""
        products = []
        
        def extract_products(obj):
            if isinstance(obj, list):
                products.extend(obj)
            elif isinstance(obj, dict):
                for v in obj.values():
                    extract_products(v)
        
        extract_products(ProductDatabase.PRODUCTS)
        return products

class StressTestGenerator:
    """Generates various test scenarios"""
    
    GREETINGS = [
        "Hi there!",
        "Hello Prime Bank",
        "Hey, how's it going?",
        "Good morning",
        "Good afternoon",
        "Good evening",
        "Welcome",
        "Greetings",
        "Hi",
        "Hello",
        "Hey",
        "What's up?",
        "How are you?",
        "Nice to meet you",
    ]
    
    PRODUCT_RETRIEVAL_QUERIES = {
        "credit_products": [
            "I need a credit card",
            "Do you have credit card options?",
            "What credit products are available?",
            "I'm looking for a credit card",
            "Tell me about your credit cards",
            "I want to apply for a credit card",
            "What's the best credit card for me?",
            "Show me credit card options",
        ],
        "savings_accounts": [
            "I want to open a savings account",
            "What savings accounts do you offer?",
            "I'm looking for a savings account",
            "Tell me about savings products",
            "What's the best savings account?",
            "I need to save money",
            "Show me savings options",
            "Do you have high-yield savings?",
        ],
        "deposit_schemes": [
            "I'm interested in fixed deposits",
            "What deposit schemes do you have?",
            "Tell me about DPS schemes",
            "I want to invest in a scheme",
            "What's the best deposit scheme?",
            "Show me term deposit options",
            "I'm looking for investment options",
            "Tell me about your deposit products",
        ],
        "youth_products": [
            "I'm young and want to save",
            "Do you have products for youth?",
            "What's the best account for students?",
            "I'm 18 and want to open an account",
            "Tell me about youth accounts",
            "I want a beginner's account",
        ],
        "senior_products": [
            "I'm 50+ and want to save",
            "Do you have senior accounts?",
            "What products for elderly customers?",
            "Tell me about 50+ accounts",
            "I'm retired and want to invest",
            "What's best for seniors?",
        ],
        "freelancer_products": [
            "I'm a freelancer, what accounts?",
            "Do you have accounts for freelancers?",
            "I need a business account",
            "What's best for self-employed?",
            "I work freelance",
        ],
        "islamic_products": [
            "I want Islamic banking",
            "Do you have Islamic products?",
            "Tell me about Shariah-compliant accounts",
            "I'm interested in Islamic banking",
            "What Islamic products do you offer?",
        ],
        "hajj_products": [
            "I want to save for Hajj",
            "Do you have Hajj schemes?",
            "Tell me about Islamic savings",
            "I want to prepare for pilgrimage",
            "What's the Hajj account?",
        ],
    }
    
    @staticmethod
    def generate_greeting_tests() -> List[Tuple[str, str]]:
        """Generate greeting test cases"""
        tests = []
        for greeting in StressTestGenerator.GREETINGS:
            tests.append(("greeting", greeting))
        return tests
    
    @staticmethod
    def generate_product_retrieval_tests() -> List[Tuple[str, str]]:
        """Generate product retrieval test cases"""
        tests = []
        for category, queries in StressTestGenerator.PRODUCT_RETRIEVAL_QUERIES.items():
            for query in queries:
                tests.append(("product_retrieval", query))
        return tests
    
    @staticmethod
    def generate_sequential_conversation_tests() -> List[List[str]]:
        """Generate multi-turn conversation sequences"""
        sequences = [
            # Sequence 1: Greeting + Credit Card interest
            ["Hello!", "I'm looking for a credit card", "Which one is best?"],
            
            # Sequence 2: Greeting + Savings inquiry
            ["Hi there", "I want to save money", "What are your best options?"],
            
            # Sequence 3: Greeting + Youth account
            ["Hey", "I'm a student", "What account should I open?"],
            
            # Sequence 4: Greeting + Islamic banking
            ["Good morning", "I want Islamic banking", "What products do you have?"],
            
            # Sequence 5: Greeting + Hajj
            ["Welcome", "I want to save for Hajj", "Tell me about the scheme"],
            
            # Sequence 6: Greeting + Multiple products
            ["Hello", "I need both credit and savings", "What do you recommend?"],
        ]
        return sequences

class StressTestRunner:
    """Runs the stress tests"""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.session_ids = {}
        self.test_count = 0
        self.success_count = 0
        self.timeout_count = 0
        self.error_count = 0
        self.response_times: List[float] = []
        self.product_matches = {}  # Track which products were recommended
    
    async def send_request(self, message: str, session_id: str = None, expected_products: List[str] = None) -> Tuple[TestResult, str]:
        """Send a single chat request and validate product recommendations"""
        if session_id is None:
            session_id = f"test_session_{self.test_count}_{int(time.time() * 1000)}"
        
        start_time = time.time()
        expected_products = expected_products or []
        
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.post(
                    f"{BASE_URL}/api/chat",
                    json={"message": message, "session_id": session_id},
                )
                
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        response_text = response_data.get("response", "").lower()
                    except:
                        response_text = ""
                    
                    # Check if expected products are mentioned in response
                    found_products = []
                    if expected_products:
                        for product in expected_products:
                            if product.lower() in response_text or product.replace('_', ' ').lower() in response_text:
                                found_products.append(product)
                    
                    result = TestResult(
                        test_name=f"Chat: {message[:40]}...",
                        status="passed",
                        response_time=response_time,
                        status_code=response.status_code,
                    )
                    result.response_text = response_text
                    
                    # Track product matches
                    if expected_products:
                        match_ratio = len(found_products) / len(expected_products) if expected_products else 0
                        if message not in self.product_matches:
                            self.product_matches[message] = {
                                "expected": expected_products,
                                "found": found_products,
                                "match_ratio": match_ratio
                            }
                    
                    self.success_count += 1
                    self.response_times.append(response_time)
                    return result, session_id
                else:
                    result = TestResult(
                        test_name=f"Chat: {message[:40]}...",
                        status="failed",
                        response_time=response_time,
                        status_code=response.status_code,
                        error_message=response.text[:200],
                    )
                    self.error_count += 1
                    return result, session_id
                    
        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            result = TestResult(
                test_name=f"Chat: {message[:40]}...",
                status="timeout",
                response_time=response_time,
                error_message=f"Request timeout after {TIMEOUT}s",
            )
            self.timeout_count += 1
            return result, session_id
        except Exception as e:
            response_time = time.time() - start_time
            result = TestResult(
                test_name=f"Chat: {message[:40]}...",
                status="failed",
                response_time=response_time,
                error_message=str(e)[:200],
            )
            self.error_count += 1
            return result, session_id
    
    async def run_specific_product_tests(self):
        """Run tests for specific product recommendations"""
        logger.info("\n" + "="*80)
        logger.info("SPECIFIC PRODUCT RECOMMENDATION TESTS")
        logger.info("="*80)
        
        # Test cases with expected products
        test_cases = [
            # Credit Cards - Conventional
            ("I need a credit card", ["visa", "mastercard", "jcb"]),
            ("I want a premium credit card", ["platinum", "world"]),
            ("Do you have Visa credit cards?", ["visa"]),
            
            # Credit Cards - Islamic
            ("I want Islamic banking credit card", ["hasanah", "visa"]),
            
            # Deposit Schemes - Conventional
            ("Tell me about DPS schemes", ["prime_kotipoti_dps", "dps", "scheme"]),
            ("I want a fixed deposit", ["fixed", "deposit", "prime_fixed_deposit"]),
            ("What about millionaire scheme?", ["millionaire", "prime_millionaire_scheme"]),
            ("I'm interested in DPS", ["dps", "kotipoti", "lakhopoti"]),
            
            # Deposit Schemes - Islamic
            ("Tell me about Islamic DPS", ["hasanah", "dps", "scheme"]),
            ("I want Hajj savings scheme", ["hajj", "hasanah", "prime_hasanah_hajj_scheme"]),
            
            # Savings Accounts - Conventional
            ("I need a youth account", ["youth", "prime_youth_account"]),
            ("What about teacher's account?", ["teacher", "prime_teachers_account"]),
            ("I'm a freelancer, what account?", ["freelancer", "prime_freelancer_account"]),
            ("Account for 50+ customers", ["50", "prime_50_plus", "atlas"]),
            
            # Savings Accounts - Islamic
            ("Islamic savings account?", ["hasanah", "prime_hasanah"]),
            ("Women's savings account?", ["women", "hasanah"]),
        ]
        
        logger.info(f"Running {len(test_cases)} specific product tests...\n")
        
        for query, expected_keywords in test_cases:
            result, _ = await self.send_request(query, expected_products=expected_keywords)
            self.results.append(result)
            self.test_count += 1
            
            status_icon = "✅" if result.status == "passed" else "❌"
            logger.info(f"{status_icon} {result.test_name[:60]}")
            logger.info(f"   Expected keywords: {', '.join(expected_keywords)}")
            
            if query in self.product_matches:
                match_data = self.product_matches[query]
                found = match_data['found'] if match_data['found'] else "None found"
                logger.info(f"   Found keywords: {found}")
            logger.info(f"   Response time: {result.response_time:.2f}s")
            
            await asyncio.sleep(0.2)
        
        logger.info(f"\n✅ Specific product tests completed")
    
    async def run_product_retrieval_tests(self):
        """Run product retrieval tests"""
        logger.info("\n" + "="*80)
        logger.info("PRODUCT RETRIEVAL TESTS")
        logger.info("="*80)
        
        tests = StressTestGenerator.generate_product_retrieval_tests()
        logger.info(f"Running {len(tests)} product retrieval queries...\n")
        
        for test_type, message in tests:
            result, _ = await self.send_request(message)
            self.results.append(result)
            self.test_count += 1
            
            status_icon = "✅" if result.status == "passed" else "❌"
            logger.info(f"{status_icon} {result.test_name[:60]} - {result.response_time:.2f}s")
            
            # Add small delay between tests to avoid overwhelming server
            await asyncio.sleep(0.1)    
    async def run_sequential_conversation_tests(self):
        """Run multi-turn conversation tests"""
        logger.info("\n" + "="*80)
        logger.info("SEQUENTIAL CONVERSATION TESTS")
        logger.info("="*80)
        
        sequences = StressTestGenerator.generate_sequential_conversation_tests()
        logger.info(f"Running {len(sequences)} multi-turn conversations...\n")
        
        for seq_idx, sequence in enumerate(sequences, 1):
            logger.info(f"--- Conversation {seq_idx} ---")
            session_id = f"conversation_{seq_idx}_{int(time.time() * 1000)}"
            
            for turn_idx, message in enumerate(sequence, 1):
                result, _ = await self.send_request(message, session_id)
                self.results.append(result)
                self.test_count += 1
                
                status_icon = "✅" if result.status == "passed" else "❌"
                logger.info(f"{status_icon} Turn {turn_idx}: {result.test_name[:50]} - {result.response_time:.2f}s")
                
                await asyncio.sleep(0.05)
            
            logger.info("")
    
    async def run_greeting_tests(self):
        """Run greeting tests"""
        logger.info("\n" + "="*80)
        logger.info("GREETING TESTS")
        logger.info("="*80)
        
        tests = StressTestGenerator.generate_greeting_tests()
        logger.info(f"Running {len(tests)} greeting variations...\n")
        
        for test_type, message in tests:
            result, _ = await self.send_request(message)
            self.results.append(result)
            self.test_count += 1
            
            status_icon = "✅" if result.status == "passed" else "❌"
            logger.info(f"{status_icon} {result.test_name[:60]} - {result.response_time:.2f}s")
    

    
    def generate_report(self):
        """Generate simplified test report"""
        logger.info("\n" + "="*80)
        logger.info("TEST SUMMARY")
        logger.info("="*80)
        
        logger.info(f"\nTotal Tests: {self.test_count}")
        logger.info(f"✅ Passed: {self.success_count}")
        logger.info(f"❌ Failed: {self.error_count}")
        logger.info(f"⏱️  Timeout: {self.timeout_count}")
        
        # Pass/Fail percentage
        pass_rate = (self.success_count / self.test_count * 100) if self.test_count > 0 else 0
        fail_rate = (self.error_count / self.test_count * 100) if self.test_count > 0 else 0
        timeout_rate = (self.timeout_count / self.test_count * 100) if self.test_count > 0 else 0
        
        logger.info(f"\nPass Rate: {pass_rate:.1f}%")
        logger.info(f"Fail Rate: {fail_rate:.1f}%")
        logger.info(f"Timeout Rate: {timeout_rate:.1f}%")
        
        # Response time stats
        if self.response_times:
            logger.info(f"\nResponse Time (seconds):")
            logger.info(f"  Min: {min(self.response_times):.2f}s")
            logger.info(f"  Max: {max(self.response_times):.2f}s")
            logger.info(f"  Mean: {statistics.mean(self.response_times):.2f}s")
        
        # Product matching stats
        if self.product_matches:
            logger.info(f"\nProduct Recommendation Accuracy:")
            total_matches = sum(m['match_ratio'] for m in self.product_matches.values())
            avg_match_ratio = total_matches / len(self.product_matches) if self.product_matches else 0
            logger.info(f"  Average Match Ratio: {avg_match_ratio*100:.1f}%")
            
            # Show detailed matches
            logger.info(f"\n  Detailed Matches:")
            for query, match_data in list(self.product_matches.items())[:10]:
                match_ratio_pct = match_data['match_ratio'] * 100
                logger.info(f"    - {query[:50]}...")
                logger.info(f"      Expected: {', '.join(match_data['expected'])}")
                logger.info(f"      Found: {match_data['found'] if match_data['found'] else 'None'}")
                logger.info(f"      Accuracy: {match_ratio_pct:.0f}%")
        
        # Failed tests
        by_status = {}
        for result in self.results:
            if result.status not in by_status:
                by_status[result.status] = []
            by_status[result.status].append(result)
        
        if by_status.get("failed"):
            logger.info(f"\n❌ Failed Tests ({len(by_status['failed'])}):")
            for result in by_status["failed"][:5]:
                logger.info(f"  - {result.test_name}: {result.error_message[:60] if result.error_message else 'Unknown error'}")
        
        # Save report
        self.save_detailed_report()
    
    def save_detailed_report(self):
        """Save detailed test report to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"stress_test_report_{timestamp}.json"
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": self.test_count,
            "passed": self.success_count,
            "failed": self.error_count,
            "timeout": self.timeout_count,
            "statistics": {
                "response_times": {
                    "min": min(self.response_times) if self.response_times else 0,
                    "max": max(self.response_times) if self.response_times else 0,
                    "mean": statistics.mean(self.response_times) if self.response_times else 0,
                    "median": statistics.median(self.response_times) if self.response_times else 0,
                }
            },
            "results": [
                {
                    "test_name": r.test_name,
                    "status": r.status,
                    "response_time": r.response_time,
                    "status_code": r.status_code,
                    "error": r.error_message,
                }
                for r in self.results
            ]
        }
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"\n📊 Detailed report saved: {filename}")

async def main():
    """Main test runner"""
    logger.info("Starting Prime Bank Chatbot Sequential Stress Test")
    logger.info(f"Target: {BASE_URL}")
    logger.info(f"Test Start: {datetime.now().isoformat()}")
    
    runner = StressTestRunner()
    
    try:
        # Phase 1: Greeting tests
        await runner.run_greeting_tests()
        await asyncio.sleep(1)
        
        # Phase 2: Product retrieval tests
        await runner.run_product_retrieval_tests()
        await asyncio.sleep(1)
        
        # Phase 3: Sequential conversation tests
        await runner.run_sequential_conversation_tests()
        await asyncio.sleep(1)
        
        # Phase 4: Specific product recommendation tests
        await runner.run_specific_product_tests()
        
    except KeyboardInterrupt:
        logger.info("\n⚠️  Test interrupted by user")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
    finally:
        runner.generate_report()
        logger.info(f"\nTest End: {datetime.now().isoformat()}")

if __name__ == "__main__":
    asyncio.run(main())
