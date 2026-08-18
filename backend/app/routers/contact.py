import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.contact import Contact
from app.models.user import User
from app.schemas.contact import ContactCreate, ContactUpdate, ContactOut

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("", response_model=list[ContactOut])
def list_contacts(company_id: Optional[uuid.UUID] = None, db: Session = Depends(get_db)):
    query = db.query(Contact)
    if company_id:
        query = query.filter(Contact.company_id == company_id)
    return query.order_by(Contact.created_at.desc()).all()


@router.post("", response_model=ContactOut, status_code=201)
def create_contact(
    payload: ContactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contact = Contact(**payload.model_dump())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@router.get("/{contact_id}", response_model=ContactOut)
def get_contact(contact_id: uuid.UUID, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.put("/{contact_id}", response_model=ContactOut)
def update_contact(
    contact_id: uuid.UUID,
    payload: ContactUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(contact, field, value)
    db.commit()
    db.refresh(contact)
    return contact


@router.delete("/{contact_id}", status_code=204)
def delete_contact(
    contact_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    db.delete(contact)
    db.commit()
