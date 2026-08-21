from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class PricingParameterOut(BaseModel):
    key: str
    label: str
    value: Decimal
    unit: Optional[str]

    class Config:
        from_attributes = True


class PricingParameterUpdate(BaseModel):
    value: Decimal
