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
    product_category: Optional[str] = None
    product_type: Optional[str] = None
    product_name: Optional[str] = None
    
    user_profile: UserProfile = Field(default_factory=UserProfile)
    
    missing_slots: List[str] = Field(default_factory=list)
    eligible_products: List[str] = Field(default_factory=list)
    comparison_mode: bool = False
    
    conversation_history: List[dict] = Field(default_factory=list)
    last_agent: Optional[str] = None
    response: str = ""
    
    class Config:
        arbitrary_types_allowed = True
