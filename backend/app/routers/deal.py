import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.deal import Deal
from app.models.enums import DealStatus
from app.schemas.deal import DealCreate, DealUpdate, DealOut

router = APIRouter(prefix="/deals", tags=["deals"])


@router.get("", response_model=list[DealOut])
def list_deals(
    company_id: Optional[uuid.UUID] = None,
    status: Optional[DealStatus] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Deal)
    if company_id:
        query = query.filter(Deal.company_id == company_id)
    if status:
        query = query.filter(Deal.status == status)
    return query.order_by(Deal.created_at.desc()).all()


@router.post("", response_model=DealOut, status_code=201)
def create_deal(payload: DealCreate, db: Session = Depends(get_db)):
    deal = Deal(**payload.model_dump())
    db.add(deal)
    db.commit()
    db.refresh(deal)
    return deal


@router.get("/{deal_id}", response_model=DealOut)
def get_deal(deal_id: uuid.UUID, db: Session = Depends(get_db)):
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return deal


@router.put("/{deal_id}", response_model=DealOut)
def update_deal(deal_id: uuid.UUID, payload: DealUpdate, db: Session = Depends(get_db)):
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(deal, field, value)
    db.commit()
    db.refresh(deal)
    return deal


@router.delete("/{deal_id}", status_code=204)
def delete_deal(deal_id: uuid.UUID, db: Session = Depends(get_db)):
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    db.delete(deal)
    db.commit()
