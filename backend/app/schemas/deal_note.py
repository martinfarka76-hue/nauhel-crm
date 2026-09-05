import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class DealNoteCreate(BaseModel):
    content: str


class DealNoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    deal_id: uuid.UUID
    author_user_id: Optional[uuid.UUID] = None
    author_name: Optional[str] = None
    content: str
    created_at: datetime
