import uuid
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict


class PartnerPriceItemBase(BaseModel):
    name: str
    wood_type: Optional[str] = None
    dimensions: Optional[str] = None
    profile: Optional[str] = None
    length: Optional[str] = None
    surface: Optional[str] = None
    service_price_per_m2: Decimal


class PartnerPriceItemCreate(PartnerPriceItemBase):
    company_id: uuid.UUID


class PartnerPriceItemUpdate(BaseModel):
    name: Optional[str] = None
    wood_type: Optional[str] = None
    dimensions: Optional[str] = None
    profile: Optional[str] = None
    length: Optional[str] = None
    surface: Optional[str] = None
    service_price_per_m2: Optional[Decimal] = None


class PartnerPriceItemOut(PartnerPriceItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
