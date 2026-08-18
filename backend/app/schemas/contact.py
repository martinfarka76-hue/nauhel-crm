import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class ContactBase(BaseModel):
    company_id: uuid.UUID
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    position: Optional[str] = None


class ContactCreate(ContactBase):
    pass


class ContactUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    position: Optional[str] = None


class ContactOut(ContactBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
