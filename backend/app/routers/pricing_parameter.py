from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.pricing_parameter import PricingParameter
from app.models.user import User
from app.schemas.pricing_parameter import PricingParameterOut, PricingParameterUpdate

router = APIRouter(prefix="/pricing-parameters", tags=["pricing-parameters"])


@router.get("", response_model=list[PricingParameterOut])
def list_pricing_parameters(db: Session = Depends(get_db)):
    return db.query(PricingParameter).order_by(PricingParameter.key).all()


@router.put("/{key}", response_model=PricingParameterOut)
def update_pricing_parameter(
    key: str,
    payload: PricingParameterUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    param = db.query(PricingParameter).filter(PricingParameter.key == key).first()
    if not param:
        raise HTTPException(status_code=404, detail="Pricing parameter not found")
    param.value = payload.value
    db.commit()
    db.refresh(param)
    return param
