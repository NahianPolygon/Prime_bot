from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, List
from enum import Enum


class BankingType(str, Enum):
    CONVENTIONAL = "conventional"
    ISLAMI = "islami"


class VerticalType(str, Enum):
    SAVE = "save"
    CREDIT = "credit"


class IntentType(str, Enum):
    ELIGIBILITY = "eligibility"
    EXPLORE = "explore"
    COMPARE = "compare"
    EXPLAIN = "explain"
    APPLY = "apply"


class IntentResult(BaseModel):
    domain: Optional[BankingType] = None
    vertical: Optional[VerticalType] = None
    intent_type: Optional[IntentType] = None
    confidence: float = Field(ge=0.0, le=1.0)
    extracted_entities: Dict = Field(default_factory=dict)


class ChatRequest(BaseModel):
    session_id: str
    user_message: str
    channel: Literal["web", "mobile"]
    language: Literal["en", "bn"] = "en"


class ChatResponse(BaseModel):
    message: str
    domain: Optional[str] = None
    vertical: Optional[str] = None
    agent: str
    sources: List[str] = Field(default_factory=list)
    confidence: float
    refusal: bool = False
