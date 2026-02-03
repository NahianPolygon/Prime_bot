from dataclasses import dataclass
from typing import List, Dict, Optional
from app.prompts.product_retrieval.recommendations import (
    DEPOSIT_RECOMMENDATION_PROMPT_TEMPLATE,
    CREDIT_CARD_RECOMMENDATION_PROMPT_TEMPLATE,
    LOANS_RECOMMENDATION_PROMPT_TEMPLATE
)

@dataclass
class SlotDefinition:
    name: str
    question: str
    keywords: List[str]
    extract_pattern: Optional[str] = None

@dataclass
class ProductGuideConfig:
    product_type: str
    display_name: str
    slots: List[SlotDefinition]
    rag_filters: Dict[str, str]
    intro_message: str
    recommendation_prompt_template: str

DEPOSIT_ACCOUNTS_CONFIG = ProductGuideConfig(
    product_type="deposits",
    display_name="Deposit Accounts",
    slots=[
        SlotDefinition(
            name="age",
            question="What's your age? This helps us suggest age-appropriate accounts.",
            keywords=["year", "old", "age", "50", "60", "70"],
            extract_pattern=r"(\d{1,3})\s*(year|years|old|yo)"
        ),
        SlotDefinition(
            name="account_goal",
            question="What's your primary goal? A) Regular savings, B) Monthly income/profit, C) Lump sum investment, or D) I'm not sure?",
            keywords=["savings", "income", "profit", "investment", "monthly", "lump sum", "wealth"],
            extract_pattern=r"(savings|income|profit|investment|monthly|lump|wealth)"
        ),
        SlotDefinition(
            name="occupation",
            question="What's your occupation? A) Student, B) Teacher, C) Salaried employee, D) Business owner, E) Retired, F) Other?",
            keywords=["student", "teacher", "salaried", "business", "freelancer", "employed", "retired"],
            extract_pattern=r"(student|teacher|salaried|business|freelancer|employed|professional|retired)"
        ),
        SlotDefinition(
            name="gender",
            question="Just to personalize recommendations, are you male or female?",
            keywords=["male", "female", "woman", "man", "lady", "gentleman"],
            extract_pattern=r"(male|female|woman|man|lady|gentleman)"
        ),
        SlotDefinition(
            name="health_benefits_interest",
            question="Are health benefits and hospital discounts important to you?",
            keywords=["health", "medical", "hospital", "doctor", "benefit", "insurance", "healthcare"],
            extract_pattern=r"(health|medical|hospital|doctor|benefit|insurance|healthcare)"
        ),
        SlotDefinition(
            name="locker_interest",
            question="Would you be interested in a safe deposit locker facility for document/jewelry storage?",
            keywords=["locker", "safe", "deposit", "security", "storage", "box", "documents", "jewelry"],
            extract_pattern=r"(locker|safe|deposit|security|storage|box|document|jewelry)"
        ),
        SlotDefinition(
            name="banking_type",
            question="Would you prefer conventional or Islamic (Shariah-compliant) banking?",
            keywords=["conventional", "islami", "islamic", "shariah", "halal"],
            extract_pattern=r"(conventional|islami|islamic|shariah)"
        ),
    ],
    rag_filters={"category": "deposit"},
    intro_message="Great! Let me help you find the best deposit account. I'll ask a few questions...",
    recommendation_prompt_template=DEPOSIT_RECOMMENDATION_PROMPT_TEMPLATE,
)

CREDIT_CARDS_CONFIG = ProductGuideConfig(
    product_type="credit_cards",
    display_name="Credit Cards",
    slots=[
        SlotDefinition(
            name="banking_type",
            question="Do you prefer conventional or Islamic (Shariah-compliant) credit cards?",
            keywords=["conventional", "islami", "islamic", "shariah"],
            extract_pattern=r"(conventional|islami|islamic|shariah)"
        ),
        SlotDefinition(
            name="spending_pattern",
            question="What's your typical spending pattern? A) Travel, B) Groceries/Shopping, C) Business, or D) All-purpose?",
            keywords=["travel", "grocery", "shopping", "business", "purpose"],
            extract_pattern=r"(travel|grocery|shopping|business|purpose)"
        ),
        SlotDefinition(
            name="card_tier_preference",
            question="What tier appeals to you? A) Gold (entry-level), B) Platinum (premium), C) World Elite (ultra-premium), or D) No preference?",
            keywords=["gold", "platinum", "world", "elite", "premium", "entry"],
            extract_pattern=r"(gold|platinum|world|elite|premium|entry)"
        ),
        SlotDefinition(
            name="annual_income",
            question="What's your approximate annual income? A) Below 5 lac, B) 5-10 lac, C) 10-20 lac, D) 20 lac+?",
            keywords=["lac", "lakh", "crore", "5 lac", "10 lac", "20 lac"],
            extract_pattern=r"(\d+)\s*(lac|lakh|crore)|below|above"
        ),
    ],
    rag_filters={"category": "credit_card"},
    intro_message="Perfect! Let me find the ideal credit card for you...",
    recommendation_prompt_template=CREDIT_CARD_RECOMMENDATION_PROMPT_TEMPLATE,
)

LOANS_CONFIG = ProductGuideConfig(
    product_type="loans",
    display_name="Loans",
    slots=[
        SlotDefinition(
            name="banking_type",
            question="Do you prefer conventional or Islamic (Shariah-compliant) loans?",
            keywords=["conventional", "islami", "islamic", "shariah"],
            extract_pattern=r"(conventional|islami|islamic|shariah)"
        ),
        SlotDefinition(
            name="loan_purpose",
            question="What's the purpose of the loan? A) Home, B) Auto, C) Personal, D) Business, E) Education?",
            keywords=["home", "auto", "personal", "business", "house", "education"],
            extract_pattern=r"(home|auto|personal|business|house|education)"
        ),
        SlotDefinition(
            name="amount_needed",
            question="Approximately how much do you need? (e.g., 5 lac, 10 lac, 50 lac)",
            keywords=["lac", "lakh", "million", "amount", "needed"],
            extract_pattern=r"(\d+)\s*(lac|lakh)"
        ),
        SlotDefinition(
            name="repayment_period",
            question="What repayment timeline suits you? A) 1-2 years, B) 3-5 years, C) 5-10 years, D) Flexible?",
            keywords=["year", "years", "month", "months", "flexible"],
            extract_pattern=r"(\d+).*year|flexible|month"
        ),
    ],
    rag_filters={"category": "loan"},
    intro_message="Let me help you find the perfect loan product...",
    recommendation_prompt_template=LOANS_RECOMMENDATION_PROMPT_TEMPLATE,
)
