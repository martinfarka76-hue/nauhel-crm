import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    notification_type: str
    message: str
    deal_id: Optional[uuid.UUID]
    document_id: Optional[uuid.UUID]
    is_read: bool
    created_at: datetime


class UnreadCountOut(BaseModel):
    unread_count: int
