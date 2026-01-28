"""Pydantic models for graph node outputs and LLM structured responses"""

from pydantic import BaseModel, Field


# Conversation Manager Models
class IntentClassification(BaseModel):
    intent: str = Field(description="User intent: explore, eligibility, compare, explain")
    banking_type: str = Field(description="Banking type: conventional or islami")
    product_category: str = Field(description="Product category: deposit, credit, investment, or other")
    confidence: float = Field(description="Confidence score 0-1")


class SlotRequirements(BaseModel):
    missing_slots: list[str] = Field(description="List of missing required slots")
    reason: str = Field(description="Explanation for why these slots are needed")


# Slot Collection Models
class SlotExtractionResult(BaseModel):
    slot_name: str = Field(description="Name of the slot being filled")
    extracted_value: str = Field(description="Extracted value from user input")
    confidence: float = Field(description="Confidence in extraction 0-1")
    is_valid: bool = Field(description="Whether the value is valid")


class SlotPromptResponse(BaseModel):
    prompt: str = Field(description="Natural prompt to ask user for the slot")
    slot_name: str = Field(description="Name of the slot being asked for")


# Eligibility Models
class EligibilityAssessment(BaseModel):
    eligible_products: list[str] = Field(description="List of eligible product names")
    reasoning: str = Field(description="Explanation of eligibility")
    recommendations: list[str] = Field(description="Recommended products to highlight")


# Product Retrieval Models
class ProductSelection(BaseModel):
    selected_products: list[str] = Field(description="List of selected product names")
    ranking_reason: str = Field(description="Explanation for ranking")


# Comparison Models
class ComparisonResult(BaseModel):
    comparison_text: str = Field(description="Detailed product comparison")
    recommendation: str = Field(description="Recommended product based on analysis")
    key_differences: list[str] = Field(description="Main differences between products")


# RAG Explanation Models
class ExplanationResult(BaseModel):
    explanation: str = Field(description="Detailed product explanation")
    key_benefits: list[str] = Field(description="Key benefits of the product")
    important_terms: dict = Field(description="Important terms and definitions")
