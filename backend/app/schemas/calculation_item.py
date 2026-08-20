import uuid
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict

from app.models.enums import ItemCategory


class CalculationItemCreate(BaseModel):
    category: ItemCategory
    name: str
    unit: Optional[str] = None
    quantity: Decimal
    unit_price: Decimal
    display_order: int = 0


class CalculationItemUpdate(BaseModel):
    category: Optional[ItemCategory] = None
    name: Optional[str] = None
    unit: Optional[str] = None
    quantity: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    display_order: Optional[int] = None


class CalculationItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    calculation_id: uuid.UUID
    category: ItemCategory
    name: str
    unit: Optional[str]
    quantity: Decimal
    unit_price: Decimal
    display_order: int
