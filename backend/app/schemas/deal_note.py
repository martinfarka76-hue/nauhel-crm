import uuid
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class DealNoteCreate(BaseModel):
    content: str
    is_task: Optional[bool] = None
    due_date: Optional[date] = None


class DealNoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    deal_id: uuid.UUID
    author_user_id: Optional[uuid.UUID] = None
    author_name: Optional[str] = None
    content: str
    is_task: Optional[bool] = None
    due_date: Optional[date] = None
    created_at: datetime
