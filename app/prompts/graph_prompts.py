from app.prompts.intent_detection import INTENT_DETECTION_PROMPT
from app.prompts.eligibility_check import ELIGIBILITY_CHECK_PROMPT
from app.prompts.product_comparison import PRODUCT_COMPARISON_PROMPT
from app.prompts.product_explanation import PRODUCT_EXPLANATION_PROMPT
from app.prompts.response_generation import RESPONSE_GENERATION_PROMPT

SLOT_COLLECTION_PROMPT = """You are a banking assistant collecting missing information from the user.

Current Missing Slots: {missing_slots}
Previous Context: {context}
User Message: {message}

Extract values for the missing slots from the user's message.
Return JSON with:
- extracted_values: dict with slot names and extracted values
- clarification_needed: bool (if you need more info)
- clarification_question: str (if clarification_needed is true)

Respond only with valid JSON."""

PRODUCT_RETRIEVAL_PROMPT = """You are a banking product expert. Find the best products for the user.

User Profile:
- Age: {age}
- Employment: {employment_type}
- Monthly Income: {monthly_income}
- Banking Type: {banking_type}
- Product Category: {product_category}

Available Products:
{available_products_json}

User Intent: {user_intent}

Return JSON with:
- recommended_products: list of product IDs/names (top 3)
- reasoning: why these products match
- next_action: suggest next step
- question: follow-up question if needed

Respond only with valid JSON."""

ELIGIBILITY_DETERMINATION_PROMPT = """You are a banking eligibility expert.

User Profile:
- Age: {age}
- Employment: {employment_type}
- Monthly Income: {monthly_income}
- Credit Score: {credit_score}
- Banking Type: {banking_type}

Product: {product_name}
Product Requirements:
{product_requirements_json}

Determine eligibility and return JSON with:
- eligible: bool
- confidence: 0.0-1.0
- reason: explanation
- missing_docs: list of documents needed
- recommendation: alternative products if not eligible

Respond only with valid JSON."""

COMPARISON_ANALYSIS_PROMPT = """You are a financial comparison expert.

User Profile:
- Income Level: {income_level}
- Priority: {priority}
- Banking Type: {banking_type}

Products to Compare:
{products_to_compare_json}

Criteria: {comparison_criteria}

Return JSON with:
- best_match: product name and why
- comparison_table: dict with pros/cons for each
- cost_analysis: fees and charges comparison
- recommendation: which to choose and why

Respond only with valid JSON."""

RAG_EXPLANATION_PROMPT = """You are a banking product expert providing detailed explanations.

Product: {product_name}
Product Details:
{product_details_json}

User Question: {user_question}

Return JSON with:
- answer: detailed answer to the question
- key_points: list of important points
- examples: real-world usage examples
- next_questions: suggested follow-up questions

Respond only with valid JSON."""

__all__ = [
    "INTENT_DETECTION_PROMPT",
    "SLOT_COLLECTION_PROMPT",
    "PRODUCT_RETRIEVAL_PROMPT",
    "ELIGIBILITY_DETERMINATION_PROMPT",
    "COMPARISON_ANALYSIS_PROMPT",
    "RAG_EXPLANATION_PROMPT",
]
