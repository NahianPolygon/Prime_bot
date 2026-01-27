from pydantic import BaseModel, Field
from typing import Optional, List


class CreditLimit(BaseModel):
    unsecured_max: int
    collateralized_max: int
    currency: str = "BDT"


class RewardPoints(BaseModel):
    earning_ratio: str
    redemption_options: List[str]


class Insurance(BaseModel):
    type: str
    death_ptd_max: int
    accidental_death_max: int
    critical_illness_max: int


class CreditCard(BaseModel):
    id: str
    name: str
    card_network: str
    tier: str
    type: str
    operating_principle: str
    credit_limits: CreditLimit
    reward_points: RewardPoints
    insurance: Insurance
    annual_fee: int
    annual_fee_waiver_condition: Optional[str] = None
    key_benefits: List[str]


class DepositAccount(BaseModel):
    id: str
    name: str
    account_type: str
    type: str
    minimum_age: int
    maximum_age: Optional[int] = None
    minimum_balance: int
    monthly_fee: int = 0
    key_features: List[str]


class DepositScheme(BaseModel):
    id: str
    name: str
    scheme_type: str
    type: str
    minimum_tenure: int
    maximum_tenure: int
    interest_rate: float
    minimum_deposit: int
    key_benefits: List[str]
