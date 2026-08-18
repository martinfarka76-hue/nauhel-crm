from pydantic import BaseModel

from app.models.enums import DealStatus


class DealTransitionRequest(BaseModel):
    to_status: DealStatus
