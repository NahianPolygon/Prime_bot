from pydantic import BaseModel
from typing import Optional


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
