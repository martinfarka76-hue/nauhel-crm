import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict

from app.models.enums import DocumentType, ItemCategory


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
    confirmed_at: Optional[datetime]
    confirmed_by_name: Optional[str] = None
    agreed_to_terms: bool = False
    amount: Optional[Decimal] = None
    idoklad_invoice_id: Optional[int] = None
    idoklad_invoice_number: Optional[str] = None
    idoklad_pdf_url: Optional[str] = None
    invoice_pdf_filename: Optional[str] = None
    delivery_note_filename: Optional[str] = None
    invoice_sent_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class CalculationItemPublicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: ItemCategory
    name: str
    unit: Optional[str]
    quantity: Decimal
    unit_price: Decimal


class CalculationPublicOut(BaseModel):
    """Veřejný souhrn kalkulace - jen zákaznicky relevantní údaje, žádná marže."""
    model_config = ConfigDict(from_attributes=True)

    product_line: Optional[str]
    wood_species: Optional[str]
    area_m2: Optional[Decimal]
    discount_material_percent: Decimal
    discount_installation_percent: Decimal
    price_without_vat: Optional[Decimal]
    vat_amount: Optional[Decimal]
    price_with_vat: Optional[Decimal]
    unit_price_per_m2: Optional[Decimal]
    valid_until: Optional[date]
    delivery_terms: Optional[str]
    payment_terms: Optional[str]
    items: list[CalculationItemPublicOut] = []


class DocumentPublicOut(BaseModel):
    """Veřejný pohled na dokument - bez interních detailů jako access_token."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_type: DocumentType
    version: int
    created_at: datetime
    confirmed_at: Optional[datetime] = None
    confirmed_by_name: Optional[str] = None
    company_name: str
    company_ico: Optional[str] = None
    company_dic: Optional[str] = None
    company_address: Optional[str] = None
    deal_name: str
    calculation: Optional[CalculationPublicOut] = None
    has_invoice_pdf: bool = False


class DocumentConfirmRequest(BaseModel):
    confirmed_by_name: str
    agreed_to_terms: bool


class DocumentConfirmResult(BaseModel):
    confirmed: bool
    confirmed_at: datetime
    confirmed_by_name: str


class DocumentViewCreateResult(BaseModel):
    document: DocumentPublicOut
    view_id: uuid.UUID


class DocumentViewDurationUpdate(BaseModel):
    duration_seconds: int


class DocumentViewOut(BaseModel):
    """Interní pohled na jednotlivé zobrazení dokumentu - pro tracking v adminu."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    viewed_at: datetime
    duration_seconds: Optional[int]
    ip_address: Optional[str]
