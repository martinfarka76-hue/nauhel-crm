import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.calculation import Calculation
from app.models.deal import Deal
from app.models.user import User
from app.schemas.calculation import CalculationCreate, CalculationUpdate, CalculationOut

router = APIRouter(tags=["calculations"])


@router.get("/deals/{deal_id}/calculations", response_model=list[CalculationOut])
def list_calculations_for_deal(deal_id: uuid.UUID, db: Session = Depends(get_db)):
    if not db.query(Deal).filter(Deal.id == deal_id).first():
        raise HTTPException(status_code=404, detail="Deal not found")
    return (
        db.query(Calculation)
        .filter(Calculation.deal_id == deal_id)
        .order_by(Calculation.created_at.desc())
        .all()
    )


@router.post("/deals/{deal_id}/calculations", response_model=CalculationOut, status_code=201)
def create_calculation(
    deal_id: uuid.UUID,
    payload: CalculationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not db.query(Deal).filter(Deal.id == deal_id).first():
        raise HTTPException(status_code=404, detail="Deal not found")

    # Jen jedna aktivní kalkulace na Deal - deaktivuj předchozí
    db.query(Calculation).filter(
        Calculation.deal_id == deal_id, Calculation.is_active.is_(True)
    ).update({"is_active": False})

    calculation = Calculation(deal_id=deal_id, is_active=True, **payload.model_dump())
    db.add(calculation)
    db.commit()
    db.refresh(calculation)
    return calculation


@router.get("/calculations/{calculation_id}", response_model=CalculationOut)
def get_calculation(calculation_id: uuid.UUID, db: Session = Depends(get_db)):
    calculation = db.query(Calculation).filter(Calculation.id == calculation_id).first()
    if not calculation:
        raise HTTPException(status_code=404, detail="Calculation not found")
    return calculation


@router.put("/calculations/{calculation_id}", response_model=CalculationOut)
def update_calculation(
    calculation_id: uuid.UUID,
    payload: CalculationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    calculation = db.query(Calculation).filter(Calculation.id == calculation_id).first()
    if not calculation:
        raise HTTPException(status_code=404, detail="Calculation not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(calculation, field, value)
    db.commit()
    db.refresh(calculation)
    return calculation


@router.delete("/calculations/{calculation_id}", status_code=204)
def delete_calculation(
    calculation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    calculation = db.query(Calculation).filter(Calculation.id == calculation_id).first()
    if not calculation:
        raise HTTPException(status_code=404, detail="Calculation not found")
    db.delete(calculation)
    db.commit()
