"""Prompt Templates - Central location for all prompts"""

from app.prompts.intent_detection import INTENT_DETECTION_PROMPT
from app.prompts.eligibility_check import ELIGIBILITY_CHECK_PROMPT
from app.prompts.product_comparison import PRODUCT_COMPARISON_PROMPT
from app.prompts.product_explanation import PRODUCT_EXPLANATION_PROMPT
from app.prompts.response_generation import RESPONSE_GENERATION_PROMPT

__all__ = [
    "INTENT_DETECTION_PROMPT",
    "ELIGIBILITY_CHECK_PROMPT",
    "PRODUCT_COMPARISON_PROMPT",
    "PRODUCT_EXPLANATION_PROMPT",
    "RESPONSE_GENERATION_PROMPT",
]
