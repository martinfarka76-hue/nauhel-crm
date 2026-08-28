from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.stage_config import StageConfig
from app.models.user import User
from app.schemas.stage_config import StageConfigOut

router = APIRouter(prefix="/stage-config", tags=["stage-config"])


@router.get("", response_model=list[StageConfigOut])
def list_stage_config(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Pravděpodobnosti uzavření pro každý stav pipeline - pro výpočet váženého objemu."""
    return db.query(StageConfig).order_by(StageConfig.display_order).all()
