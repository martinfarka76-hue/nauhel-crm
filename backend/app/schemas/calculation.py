import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict


class CalculationCreate(BaseModel):
    """
    Vytvoření kalkulace - jen "hlavička", žádná cena. Cena se dopočítá
    až z položek (CalculationItem), viz POST /calculations/{id}/items.
    """
    product_line: Optional[str] = None
    wood_species: Optional[str] = None
    area_m2: Optional[Decimal] = None
    distance_km: Optional[Decimal] = None
    vat_rate: Optional[Decimal] = None
    discount_material_percent: Decimal = Decimal("0")
    discount_installation_percent: Decimal = Decimal("0")
    valid_until: Optional[date] = None
    raw_snapshot: Optional[dict[str, Any]] = None


class CalculationUpdate(BaseModel):
    product_line: Optional[str] = None
    wood_species: Optional[str] = None
    area_m2: Optional[Decimal] = None
    distance_km: Optional[Decimal] = None
    vat_rate: Optional[Decimal] = None
    discount_material_percent: Optional[Decimal] = None
    discount_installation_percent: Optional[Decimal] = None
    valid_until: Optional[date] = None
    raw_snapshot: Optional[dict[str, Any]] = None


class CalculationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    deal_id: uuid.UUID
    is_active: bool
    product_line: Optional[str]
    wood_species: Optional[str]
    area_m2: Optional[Decimal]
    distance_km: Optional[Decimal]
    vat_rate: Optional[Decimal]
    discount_material_percent: Decimal
    discount_installation_percent: Decimal
    # Vypočtené - read only, viz calculation_totals.py
    price_without_vat: Optional[Decimal]
    vat_amount: Optional[Decimal]
    price_with_vat: Optional[Decimal]
    unit_price_per_m2: Optional[Decimal]
    margin_total: Optional[Decimal]
    valid_until: Optional[date]
    raw_snapshot: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime
