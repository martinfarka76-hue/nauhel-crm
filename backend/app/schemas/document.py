import uuid
from datetime import datetime
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


class DocumentPublicOut(BaseModel):
    """Veřejný pohled na dokument - bez interních detailů jako access_token."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_type: DocumentType
    version: int
    created_at: datetime


class DocumentViewCreateResult(BaseModel):
    document: DocumentPublicOut
    view_id: uuid.UUID


class DocumentViewDurationUpdate(BaseModel):
    duration_seconds: int
