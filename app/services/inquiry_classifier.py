import re
import logging
from typing import Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ExtractedContext(BaseModel):
    banking_type: Optional[str] = None
    employment: Optional[str] = None
    product_category: Optional[str] = None
    product_tier: Optional[str] = None
    age: Optional[int] = None
    income: Optional[int] = None
    keywords: list = []
    use_cases: list = []


class InquiryClassification(BaseModel):
    inquiry_type: str
    confidence: float
    extracted_context: ExtractedContext
    reasoning: str


class InquiryClassifier:
    
    PRODUCT_KEYWORDS = {
        'credit_card': ['credit card', 'card', 'visa', 'mastercard', 'jcb', 'hasanah gold', 'hasanah platinum'],
        'savings_account': ['savings account', 'account', 'deposit', 'saving', 'current account', 'personal account'],
        'deposit_scheme': ['deposit scheme', 'dps', 'fdr', 'fixed deposit', 'scheme', 'millionaire', 'kotipoti', 'lakhopoti']
    }
    
    PRODUCT_QUERY_KEYWORDS = [
        'show me', 'what', 'list', 'options', 'available', 'do you have', 'tell me about',
        'product', 'cards', 'accounts', 'schemes', 'features', 'benefits', 'compare'
    ]
    
    ELIGIBILITY_KEYWORDS = [
        'am i eligible', 'can i', 'do i qualify', 'am i qualified', 'will i be approved',
        'check if', 'eligible for', 'qualify for', 'apply for', 'get a', 'open a', 'apply'
    ]
    
    EMPLOYMENT_TYPES = {
        'salaried': ['salaried', 'salary', 'employed', 'job', 'office'],
        'self_employed': ['self employed', 'self-employed', 'freelancer', 'freelance', 'contractor'],
        'business_owner': ['business owner', 'entrepreneur', 'businessman', 'businesswoman', 'business'],
        'student': ['student', 'studying', 'university', 'college', 'school'],
        'retired': ['retired', 'retirement', 'pensioner', 'pension']
    }
    
    BANKING_TYPES = {
        'islami': ['islamic', 'islami', 'sharia', 'shariah', 'hasanah'],
        'conventional': ['conventional', 'regular', 'interest-based']
    }
    
    GREETING_PATTERNS = [
        r'\b(hi|hello|hey|greetings?|good morning|good afternoon|good evening|what\'?s up|howdy)\b',
        r'^(hi|hello|hey|hey there)[\s,!]*$',
        r'\bhow are you\b',
        r'\bnice to meet you\b'
    ]
    
    @classmethod
    def classify(cls, user_message: str) -> InquiryClassification:
        message = user_message.lower().strip()
        
        if cls._is_greeting(message):
            return InquiryClassification(
                inquiry_type="GREETING",
                confidence=0.95,
                extracted_context=ExtractedContext(),
                reasoning="Message is a greeting"
            )
        
        banking_type = cls._extract_banking_type(message)
        employment = cls._extract_employment(message)
        product_category, keywords = cls._extract_product_info(message)
        age = cls._extract_age(message)
        income = cls._extract_income(message)
        
        is_product_query = cls._is_product_query(message, keywords)
        is_eligibility_query = cls._is_eligibility_query(message)
        
        if is_product_query and not is_eligibility_query:
            confidence = 0.85 if len(keywords) >= 1 else 0.7
            return InquiryClassification(
                inquiry_type="PRODUCT_INFO_QUERY",
                confidence=confidence,
                extracted_context=ExtractedContext(
                    banking_type=banking_type,
                    employment=employment,
                    product_category=product_category,
                    keywords=keywords
                ),
                reasoning=f"Product query detected with keywords: {keywords}"
            )
        
        if is_product_query and is_eligibility_query:
            confidence = 0.8 if (age or income or employment) else 0.65
            return InquiryClassification(
                inquiry_type="MIXED_QUERY",
                confidence=confidence,
                extracted_context=ExtractedContext(
                    banking_type=banking_type,
                    employment=employment,
                    product_category=product_category,
                    age=age,
                    income=income,
                    keywords=keywords
                ),
                reasoning="User asking about products AND eligibility"
            )
        
        confidence = 0.8 if (age or income or employment) else 0.5
        return InquiryClassification(
            inquiry_type="ELIGIBILITY_QUERY",
            confidence=confidence,
            extracted_context=ExtractedContext(
                banking_type=banking_type,
                employment=employment,
                product_category=product_category,
                age=age,
                income=income,
                keywords=keywords
            ),
            reasoning="Defaulting to eligibility assessment"
        )
    
    @classmethod
    def _is_greeting(cls, message: str) -> bool:
        for pattern in cls.GREETING_PATTERNS:
            if re.search(pattern, message, re.IGNORECASE):
                return True
        return False
    
    @classmethod
    def _is_product_query(cls, message: str, keywords: list) -> bool:
        if keywords:
            return True
        
        for keyword in cls.PRODUCT_QUERY_KEYWORDS:
            if keyword in message:
                return True
        return False
    
    @classmethod
    def _is_eligibility_query(cls, message: str) -> bool:
        for keyword in cls.ELIGIBILITY_KEYWORDS:
            if keyword in message:
                return True
        return False
    
    @classmethod
    def _extract_banking_type(cls, message: str) -> Optional[str]:
        for banking_type, keywords in cls.BANKING_TYPES.items():
            for keyword in keywords:
                if keyword in message:
                    return banking_type
        return None
    
    @classmethod
    def _extract_employment(cls, message: str) -> Optional[str]:
        for employment_type, keywords in cls.EMPLOYMENT_TYPES.items():
            for keyword in keywords:
                if keyword in message:
                    return employment_type
        return None
    
    @classmethod
    def _extract_product_info(cls, message: str) -> tuple:
        keywords = []
        product_category = None
        
        for category, product_keywords in cls.PRODUCT_KEYWORDS.items():
            for keyword in product_keywords:
                if keyword in message:
                    keywords.append(keyword)
                    if not product_category:
                        product_category = category.replace('_', ' ')
        
        tiers = ['gold', 'platinum', 'world', 'elite', 'premium', 'basic', 'standard']
        for tier in tiers:
            if tier in message:
                keywords.append(tier)
        
        use_cases = []
        use_case_patterns = {
            'international': ['international', 'travel', 'abroad', 'overseas'],
            'cashback': ['cashback', 'cash back', 'reward', 'rewards'],
            'lounge': ['lounge', 'airport', 'vip'],
            'dining': ['dining', 'restaurant', 'food'],
            'daily_expenses': ['daily', 'everyday', 'regular'],
            'savings': ['save', 'saving', 'accumulate'],
            'investment': ['invest', 'investment', 'grow']
        }
        
        for use_case, patterns in use_case_patterns.items():
            for pattern in patterns:
                if pattern in message:
                    use_cases.append(use_case)
                    break
        
        return product_category, keywords
    
    @classmethod
    def _extract_age(cls, message: str) -> Optional[int]:
        age_patterns = [
            r'\b(\d{2})\s*(?:years?|yr?|old|age)\b',
            r'\b(?:age|i\'m|i am|i\'m)\s*(\d{1,3})\b',
            r'\b(\d{2})\s*y\.o\.?\b'
        ]
        
        for pattern in age_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                age = int(match.group(1))
                if 18 <= age <= 120:
                    return age
        return None
    
    @classmethod
    def _extract_income(cls, message: str) -> Optional[float]:
        income_patterns = [
            r'(?:income|earn|earning|salary|salary is|monthly|yearly|annual|per month|per year)\s*(?:of\s*)?(?:tk\.?|taka|৳)?\s*([0-9,]+)',
            r'([0-9,]+)\s*(?:tk\.?|taka|৳)?(?:\s*(?:per|\/)\s*(?:month|year|annum))?',
            r'(?:earn|earning|make)\s*(?:tk\.?|taka|৳)?\s*([0-9,]+)'
        ]
        
        for pattern in income_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                try:
                    income_str = match.group(1).replace(',', '')
                    income = float(income_str)
                    if income > 0:
                        return income
                except (ValueError, AttributeError):
                    continue
        return None
