import re
import logging
import json
from typing import Optional
from app.core.config import Settings
from app.models.services.inquiry import ExtractedContext, InquiryClassification

logger = logging.getLogger(__name__)
settings = Settings()

class InquiryClassifier:
    def __init__(self):
        self._build_patterns()
        self.llm = None
    
    def _get_llm(self):
        """Lazy load Google Generative AI client"""
        if self.llm is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.google_api_key)
                self.llm = genai.GenerativeModel('gemini-2.5-flash-lite')
            except Exception as e:
                logger.warning(f"Failed to initialize LLM: {e}. Using fallback keyword matching.")
                self.llm = None
        return self.llm

    def _build_patterns(self):
        """Minimal hardcoded patterns - only basic fallback regex patterns"""
        # Basic greeting regex - used as fallback
        self.basic_greeting_patterns = [
            r'\b(hi|hello|hey|greetings?|good morning|good afternoon|good evening|what\'?s up|howdy|sup|yo|heya)\b',
            r'^(hi|hello|hey|hey there)[\s,!]*$'
        ]
        
        # Basic banking terms - used for extraction fallback
        self.banking_term_patterns = {
            'banking_type': {
                'islami': ['islamic', 'islami', 'shariah', 'halal'],
                'conventional': ['conventional', 'regular', 'standard']
            },
            'employment': {
                'salaried': ['salaried', 'job', 'employed', 'engineer', 'teacher', 'doctor', 'manager', 'staff', 'officer', 'executive', 'analyst'],
                'business_owner': ['business', 'self-employed', 'entrepreneur', 'freelance', 'startup']
            }
        }

    def classify(self, user_message: str) -> InquiryClassification:
        """Classify user inquiry using LLM with fallback to keyword matching"""
        message = user_message.lower().strip()
        
        # Fast path: detect greeting with basic regex
        if self._is_greeting(message):
            return InquiryClassification(
                inquiry_type="GREETING",
                confidence=0.95,
                extracted_context=ExtractedContext(),
                reasoning="Message is a greeting"
            )
        
        # Try LLM-based classification
        llm = self._get_llm()
        if llm:
            return self._classify_with_llm(user_message, llm)
        else:
            # Fallback to keyword matching if LLM unavailable
            return self._classify_with_keywords(message)
    
    def _classify_with_llm(self, user_message: str, llm) -> InquiryClassification:
        """Classify using LLM prompt-based detection with timeout"""
        try:
            prompt = f"""Analyze this banking user message and classify it. Return JSON with these fields:
- inquiry_type: one of [PRODUCT_INFO_QUERY, COMPARISON_QUERY, ELIGIBILITY_QUERY, GENERAL_QUESTION]
- confidence: 0.0-1.0
- banking_type: 'conventional' or 'islami' if mentioned, else null
- product_category: detected product type (credit_card, savings_account, deposit_scheme, loan, investment) if any, else null
- age: extracted age if mentioned, else null
- income: extracted annual income if mentioned, else null
- employment: employment type if mentioned, else null
- keywords: list of relevant banking keywords found
- reasoning: brief explanation

Message: "{user_message}"

Return ONLY valid JSON, no markdown or extra text."""

            # Set timeout to 10 seconds to avoid hanging on slow LLM responses
            import time
            start = time.time()
            
            response = llm.generate_content(prompt, timeout=10)
            
            elapsed = time.time() - start
            logger.debug(f"LLM classification took {elapsed:.2f}s for: {user_message[:50]}")
            
            result_text = response.text.strip()
            
            # Parse JSON response
            if result_text.startswith('```'):
                result_text = result_text.split('```')[1]
                if result_text.startswith('json'):
                    result_text = result_text[4:]
            
            result = json.loads(result_text)
            
            return InquiryClassification(
                inquiry_type=result.get('inquiry_type', 'GENERAL_QUESTION'),
                confidence=float(result.get('confidence', 0.5)),
                extracted_context=ExtractedContext(
                    banking_type=result.get('banking_type'),
                    product_category=result.get('product_category'),
                    age=result.get('age'),
                    income=result.get('income'),
                    employment=result.get('employment'),
                    keywords=result.get('keywords', [])
                ),
                reasoning=result.get('reasoning', 'LLM-based classification')
            )
        except Exception as e:
            logger.warning(f"LLM classification timeout/error: {e}. Falling back to keyword matching.")
            return self._classify_with_keywords(user_message.lower())
    
    def _classify_with_keywords(self, message: str) -> InquiryClassification:
        """Fallback keyword-based classification"""
        product_category = self._extract_product_category_keywords(message)
        banking_type = self._extract_banking_type_keywords(message)
        keywords = self._extract_keywords(message)
        age = self._extract_age(message)
        income = self._extract_income(message)
        employment = self._extract_employment_keywords(message)
        
        # Detect intent using semantic keywords
        is_comparison = self._detect_comparison_intent(message)
        is_eligibility = self._detect_eligibility_intent(message)
        is_product_query = self._detect_product_intent(message, product_category, keywords)
        
        if is_comparison:
            return InquiryClassification(
                inquiry_type="COMPARISON_QUERY",
                confidence=0.85,
                extracted_context=ExtractedContext(
                    banking_type=banking_type,
                    product_category=product_category,
                    keywords=keywords
                ),
                reasoning="Comparison intent detected (fallback keywords)"
            )
        
        if is_eligibility and (age or income or employment):
            return InquiryClassification(
                inquiry_type="ELIGIBILITY_QUERY",
                confidence=0.85,
                extracted_context=ExtractedContext(
                    banking_type=banking_type,
                    product_category=product_category,
                    age=age,
                    income=income,
                    employment=employment,
                    keywords=keywords
                ),
                reasoning="Eligibility check detected (fallback keywords)"
            )
        
        if is_product_query:
            return InquiryClassification(
                inquiry_type="PRODUCT_INFO_QUERY",
                confidence=0.8,
                extracted_context=ExtractedContext(
                    banking_type=banking_type,
                    product_category=product_category,
                    keywords=keywords
                ),
                reasoning="Product inquiry intent detected (fallback keywords)"
            )
        
        return InquiryClassification(
            inquiry_type="GENERAL_QUESTION",
            confidence=0.6,
            extracted_context=ExtractedContext(
                banking_type=banking_type,
                product_category=product_category,
                keywords=keywords
            ),
            reasoning="General banking question (fallback keywords)"
        )
    
    def _detect_comparison_intent(self, message: str) -> bool:
        """Detect comparison intent semantically"""
        comparison_indicators = ['compare', 'difference', 'better', 'vs', 'versus', 'which is', 'which is better', 'prefer', 'more suitable']
        return any(indicator in message for indicator in comparison_indicators)
    
    def _detect_eligibility_intent(self, message: str) -> bool:
        """Detect eligibility checking intent"""
        eligibility_indicators = ['eligible', 'qualify', 'qualified', 'approved', 'approve', 'approval', 'requirements', 'require', 'eligible for', 'can i get', 'am i']
        return any(indicator in message for indicator in eligibility_indicators)
    
    def _detect_product_intent(self, message: str, product_category: Optional[str], keywords: list) -> bool:
        """Detect product inquiry intent"""
        product_intent_indicators = [
            'save', 'savings', 'deposit', 'loan', 'invest', 'investment',
            'scheme', 'card', 'account', 'goal', 'interest', 'borrow', 'credit', 'interest rate', 'benefits'
        ]
        action_indicators = ['show', 'list', 'what', 'tell', 'available', 'interested', 'want', 'need', 'looking', 'find', 'get', 'open']
        
        has_product_intent = any(ind in message for ind in product_intent_indicators)
        has_action = any(ind in message for ind in action_indicators)
        
        return product_category or has_product_intent or (has_action and keywords) or len(keywords) > 0
    
    def _is_greeting(self, message: str) -> bool:
        """Fast greeting detection with basic regex"""
        return any(re.search(pattern, message, re.IGNORECASE) for pattern in self.basic_greeting_patterns)
    
    def _extract_product_category_keywords(self, message: str) -> Optional[str]:
        """Extract product category from keywords (fallback)"""
        product_patterns = {
            'credit_card': ['credit card', 'card', 'credit limit', 'cashback', 'reward'],
            'savings_account': ['savings account', 'account', 'deposit', 'interest', 'savings'],
            'deposit_scheme': ['deposit scheme', 'scheme', 'dps', 'fixed deposit'],
            'loan': ['loan', 'borrowing', 'borrow', 'credit facility'],
            'investment': ['invest', 'investment', 'mutual fund', 'portfolio']
        }
        
        for category, keywords in product_patterns.items():
            if any(kw in message for kw in keywords):
                return category
        return None
    
    def _extract_banking_type_keywords(self, message: str) -> Optional[str]:
        """Extract banking type from keywords (fallback)"""
        for banking_type, keywords in self.banking_term_patterns['banking_type'].items():
            if any(word in message for word in keywords):
                return banking_type
        return None
    
    def _extract_employment_keywords(self, message: str) -> Optional[str]:
        """Extract employment type from keywords (fallback)"""
        for emp_type, keywords in self.banking_term_patterns['employment'].items():
            if any(word in message for word in keywords):
                return emp_type
        return None
    
    def _extract_keywords(self, message: str) -> list:
        """Extract relevant banking keywords (fallback)"""
        keywords = []
        keyword_list = ['credit', 'savings', 'deposit', 'rewards', 'cashback', 'travel', 'lounge', 'insurance', 'fee', 'interest', 'limit', 'tenure', 'rate']
        
        for keyword in keyword_list:
            if keyword in message:
                keywords.append(keyword)
        
        return keywords
    
    def _extract_employment(self, message: str) -> Optional[str]:
        """Extract employment type (wrapper for fallback)"""
        return self._extract_employment_keywords(message)
    
    def _extract_age(self, message: str) -> Optional[int]:
        patterns = [
            r'(\d+)\s*years?\s*old',
            r'age[:\s]+(\d+)',
            r'i\s*(?:am|\'m)\s*(\d+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, message)
            if match:
                try:
                    return int(match.group(1))
                except:
                    pass
        return None

    def _extract_income(self, message: str) -> Optional[int]:
        patterns = [
            r'(?:annual\s*)?income[:\s]+(\d+)',
            r'(?:earn|earning)[:\s]+(?:annually|per year)[:\s]*(\d+)',
            r'(\d+)\s*(?:annual income|yearly income|per year)',
            r'(?:income|earning)[:\s]*(?:of\s*)?(?:around\s*)?(?:approx\s*)?(\d+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, message)
            if match:
                try:
                    return int(match.group(1))
                except:
                    pass
        return None
