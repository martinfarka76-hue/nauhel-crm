import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

from app.models.enums import CustomerType


class CompanyBase(BaseModel):
    name: str
    ico: Optional[str] = None
    dic: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    is_partner: bool = False
    customer_type: CustomerType = CustomerType.PODNIKATEL


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    ico: Optional[str] = None
    dic: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    is_partner: Optional[bool] = None
    customer_type: Optional[CustomerType] = None


class CompanyOut(CompanyBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    idoklad_contact_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
