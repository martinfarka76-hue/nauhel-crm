from pydantic import BaseModel, ConfigDict


class StageConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    stage_name: str
    probability_percent: int
    display_order: int
