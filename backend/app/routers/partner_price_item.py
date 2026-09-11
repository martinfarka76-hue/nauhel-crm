import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.partner_price_item import PartnerPriceItem
from app.models.user import User
from app.schemas.partner_price_item import (
    PartnerPriceItemCreate,
    PartnerPriceItemUpdate,
    PartnerPriceItemOut,
)

router = APIRouter(prefix="/partner-price-items", tags=["partner-price-items"])


@router.get("", response_model=list[PartnerPriceItemOut])
def list_partner_price_items(
    company_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(PartnerPriceItem)
    if company_id:
        query = query.filter(PartnerPriceItem.company_id == company_id)
    return query.order_by(PartnerPriceItem.name).all()


@router.post("", response_model=PartnerPriceItemOut, status_code=201)
def create_partner_price_item(
    payload: PartnerPriceItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = PartnerPriceItem(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{item_id}", response_model=PartnerPriceItemOut)
def update_partner_price_item(
    item_id: uuid.UUID,
    payload: PartnerPriceItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.query(PartnerPriceItem).filter(PartnerPriceItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Partner price item not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
def delete_partner_price_item(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.query(PartnerPriceItem).filter(PartnerPriceItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Partner price item not found")
    db.delete(item)
    db.commit()
