import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import get_current_user
from app.core.calculation_totals import recompute_calculation_totals
from app.models.calculation import Calculation
from app.models.calculation_item import CalculationItem
from app.models.deal import Deal
from app.models.user import User
from app.schemas.calculation import CalculationCreate, CalculationUpdate, CalculationOut
from app.schemas.calculation_item import CalculationItemCreate, CalculationItemUpdate, CalculationItemOut

router = APIRouter(tags=["calculations"])


def _get_calculation_or_404(db: Session, calculation_id: uuid.UUID) -> Calculation:
    calculation = db.query(Calculation).filter(Calculation.id == calculation_id).first()
    if not calculation:
        raise HTTPException(status_code=404, detail="Calculation not found")
    return calculation


# --- Calculation (hlavička) ---

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
    return _get_calculation_or_404(db, calculation_id)


@router.put("/calculations/{calculation_id}", response_model=CalculationOut)
def update_calculation(
    calculation_id: uuid.UUID,
    payload: CalculationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    calculation = _get_calculation_or_404(db, calculation_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(calculation, field, value)
    db.commit()
    # Slevy nebo area_m2 se mohly změnit - přepočti ceny
    return recompute_calculation_totals(db, calculation)


@router.delete("/calculations/{calculation_id}", status_code=204)
def delete_calculation(
    calculation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    calculation = _get_calculation_or_404(db, calculation_id)
    db.delete(calculation)
    db.commit()


# --- CalculationItem (řádkové položky) ---

@router.get("/calculations/{calculation_id}/items", response_model=list[CalculationItemOut])
def list_calculation_items(calculation_id: uuid.UUID, db: Session = Depends(get_db)):
    _get_calculation_or_404(db, calculation_id)
    return (
        db.query(CalculationItem)
        .filter(CalculationItem.calculation_id == calculation_id)
        .order_by(CalculationItem.display_order)
        .all()
    )


@router.post("/calculations/{calculation_id}/items", response_model=CalculationOut, status_code=201)
def create_calculation_item(
    calculation_id: uuid.UUID,
    payload: CalculationItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Vrací aktualizovanou Calculation (s přepočtenými cenami), ne samotnou položku."""
    calculation = _get_calculation_or_404(db, calculation_id)
    item = CalculationItem(calculation_id=calculation_id, **payload.model_dump())
    db.add(item)
    db.commit()
    return recompute_calculation_totals(db, calculation)


@router.put("/calculation-items/{item_id}", response_model=CalculationOut)
def update_calculation_item(
    item_id: uuid.UUID,
    payload: CalculationItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.query(CalculationItem).filter(CalculationItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Calculation item not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    calculation = _get_calculation_or_404(db, item.calculation_id)
    return recompute_calculation_totals(db, calculation)


@router.delete("/calculation-items/{item_id}", response_model=CalculationOut)
def delete_calculation_item(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.query(CalculationItem).filter(CalculationItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Calculation item not found")
    calculation_id = item.calculation_id
    db.delete(item)
    db.commit()
    calculation = _get_calculation_or_404(db, calculation_id)
    return recompute_calculation_totals(db, calculation)
