from pydantic import BaseModel, Field
from typing import Optional, List


class UserProfile(BaseModel):
    age: Optional[int] = None
    religion: Optional[str] = None
    employment_type: Optional[str] = None
    income_monthly: Optional[float] = None
    income_yearly: Optional[float] = None
    income_verified: bool = False
    deposit: Optional[float] = None
    credit_score: Optional[int] = None


class IncomeInfo(BaseModel):
    amount: Optional[float] = None
    frequency: Optional[str] = None
    verified: bool = False


class ConversationState(BaseModel):
    session_id: str
    
    inquiry_type: Optional[str] = None
    inquiry_confidence: float = 0.0
    extracted_context: dict = Field(default_factory=dict)
    matched_products: List[dict] = Field(default_factory=list)
    
    intent: Optional[str] = None
    banking_type: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    remittance_status: Optional[str] = None
    product_category: Optional[str] = None
    product_type: Optional[str] = None
    product_name: Optional[str] = None
    account_goal: Optional[str] = None
    account_purpose: Optional[str] = None
    account_type_preference: Optional[str] = None
    health_benefits_interest: Optional[str] = None
    locker_interest: Optional[str] = None
    occupation: Optional[str] = None
    spending_pattern: Optional[str] = None
    card_tier_preference: Optional[str] = None
    annual_income: Optional[str] = None
    loan_purpose: Optional[str] = None
    amount_needed: Optional[str] = None
    repayment_period: Optional[str] = None
    monthly_savings: Optional[str] = None
    primary_use: Optional[str] = None
    travel_frequency: Optional[str] = None
    credit_tier: Optional[str] = None
    loan_amount: Optional[str] = None
    repayment_tenure: Optional[str] = None
    
    user_profile: UserProfile = Field(default_factory=UserProfile)
    
    missing_slots: List[str] = Field(default_factory=list)
    eligible_products: List[str] = Field(default_factory=list)
    suggested_products: List[dict] = Field(default_factory=list)
    comparison_products: List[dict] = Field(default_factory=list)
    comparison_mode: bool = False
    
    products_identified: bool = False
    clarification_message: Optional[str] = None
    comparison_status: Optional[str] = None
    
    comparison_banking_type: Optional[str] = None
    comparison_deposit_frequency: Optional[str] = None
    comparison_tenure_range: Optional[str] = None
    comparison_purpose: Optional[str] = None
    comparison_interest_priority: Optional[str] = None
    comparison_flexibility_priority: Optional[str] = None
    comparison_feature_priorities: List[str] = Field(default_factory=list)
    comparison_initial_budget: Optional[float] = None
    comparison_monthly_budget: Optional[float] = None
    comparison_collected_slots: List[str] = Field(default_factory=list)
    comparison_slot_to_collect: Optional[str] = None
    comparison_product_type: Optional[str] = None  # Product type being compared (deposits, credit_cards, loans)
    
    product_type_in_progress: Optional[str] = None
    current_slot: Optional[str] = None
    next_action: Optional[str] = None  # For subgraph routing
    
    conversation_history: List[dict] = Field(default_factory=list)
    last_agent: Optional[str] = None
    response: str = ""
    
    class Config:
        arbitrary_types_allowed = True
