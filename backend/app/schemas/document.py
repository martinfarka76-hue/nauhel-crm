import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict

from app.models.enums import DocumentType


class DocumentCreate(BaseModel):
    calculation_id: Optional[uuid.UUID] = None
    document_type: DocumentType
    version: int = 1


class DocumentUpdate(BaseModel):
    email_sent_at: Optional[datetime] = None


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    deal_id: uuid.UUID
    calculation_id: Optional[uuid.UUID]
    document_type: DocumentType
    version: int
    access_token: str
    email_sent_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class CalculationPublicOut(BaseModel):
    """Veřejný souhrn kalkulace - jen zákaznicky relevantní údaje, žádná marže."""
    model_config = ConfigDict(from_attributes=True)

    product_line: Optional[str]
    wood_species: Optional[str]
    area_m2: Optional[Decimal]
    price_without_vat: Optional[Decimal]
    vat_amount: Optional[Decimal]
    price_with_vat: Optional[Decimal]
    unit_price_per_m2: Optional[Decimal]


class DocumentPublicOut(BaseModel):
    """Veřejný pohled na dokument - bez interních detailů jako access_token."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_type: DocumentType
    version: int
    created_at: datetime
    company_name: str
    deal_name: str
    calculation: Optional[CalculationPublicOut] = None


class DocumentViewCreateResult(BaseModel):
    document: DocumentPublicOut
    view_id: uuid.UUID


class DocumentViewDurationUpdate(BaseModel):
    duration_seconds: int
