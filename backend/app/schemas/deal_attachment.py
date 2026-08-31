import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class DealAttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    deal_id: uuid.UUID
    original_filename: str
    content_type: Optional[str] = None
    uploaded_at: datetime
