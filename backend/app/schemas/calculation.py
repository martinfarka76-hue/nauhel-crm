import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict


class CalculationBase(BaseModel):
    product_line: Optional[str] = None
    wood_species: Optional[str] = None
    area_m2: Optional[Decimal] = None
    distance_km: Optional[Decimal] = None
    vat_rate: Optional[Decimal] = None
    price_without_vat: Optional[Decimal] = None
    vat_amount: Optional[Decimal] = None
    price_with_vat: Optional[Decimal] = None
    unit_price_per_m2: Optional[Decimal] = None
    margin_total: Optional[Decimal] = None
    raw_snapshot: Optional[dict[str, Any]] = None


class CalculationCreate(CalculationBase):
    pass


class CalculationUpdate(CalculationBase):
    pass


class CalculationOut(CalculationBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    deal_id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
