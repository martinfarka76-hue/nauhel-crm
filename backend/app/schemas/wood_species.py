import uuid
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict


class WoodSpeciesCreate(BaseModel):
    name: str
    width_mm: Optional[Decimal] = None
    width_effective_mm: Optional[Decimal] = None
    length_mm: Optional[Decimal] = None
    thickness_mm: Optional[Decimal] = None
    purchase_price_per_m2: Optional[Decimal] = None
    supplier: Optional[str] = None
    notes: Optional[str] = None


class WoodSpeciesUpdate(BaseModel):
    name: Optional[str] = None
    width_mm: Optional[Decimal] = None
    width_effective_mm: Optional[Decimal] = None
    length_mm: Optional[Decimal] = None
    thickness_mm: Optional[Decimal] = None
    purchase_price_per_m2: Optional[Decimal] = None
    supplier: Optional[str] = None
    notes: Optional[str] = None


class WoodSpeciesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    width_mm: Optional[Decimal]
    width_effective_mm: Optional[Decimal]
    length_mm: Optional[Decimal]
    thickness_mm: Optional[Decimal]
    purchase_price_per_m2: Optional[Decimal]
    supplier: Optional[str]
    notes: Optional[str]
