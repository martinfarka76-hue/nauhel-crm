import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict

from app.models.enums import DealStatus


class DealBase(BaseModel):
    company_id: uuid.UUID
    contact_id: Optional[uuid.UUID] = None
    owner_user_id: Optional[uuid.UUID] = None
    name: str
    status: DealStatus = DealStatus.LEAD
    price: Optional[Decimal] = None
    expected_close_date: Optional[date] = None
    expected_invoice_date: Optional[date] = None
    deposit_paid: bool = False


class DealCreate(DealBase):
    pass


class DealUpdate(BaseModel):
    contact_id: Optional[uuid.UUID] = None
    owner_user_id: Optional[uuid.UUID] = None
    name: Optional[str] = None
    status: Optional[DealStatus] = None
    price: Optional[Decimal] = None
    expected_close_date: Optional[date] = None
    expected_invoice_date: Optional[date] = None
    deposit_paid: Optional[bool] = None


class DealOut(DealBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sharepoint_folder_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
