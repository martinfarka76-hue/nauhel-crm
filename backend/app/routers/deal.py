import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import get_current_user
from app.core.deal_transitions import perform_transition
from app.models.deal import Deal
from app.models.deal_note import DealNote
from app.models.document import Document
from app.models.enums import DealStatus, DocumentType
from app.models.user import User
from app.schemas.deal import DealCreate, DealUpdate, DealOut
from app.schemas.deal_transition import DealTransitionRequest

router = APIRouter(prefix="/deals", tags=["deals"])


@router.get("", response_model=list[DealOut])
def list_deals(
    company_id: Optional[uuid.UUID] = None,
    status: Optional[DealStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Deal)
    if company_id:
        query = query.filter(Deal.company_id == company_id)
    if status:
        query = query.filter(Deal.status == status)
    return query.order_by(Deal.created_at.desc()).all()


@router.post("", response_model=DealOut, status_code=201)
def create_deal(
    payload: DealCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deal = Deal(**payload.model_dump())
    db.add(deal)
    db.commit()
    db.refresh(deal)
    return deal


@router.get("/{deal_id}", response_model=DealOut)
def get_deal(deal_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return deal


@router.put("/{deal_id}", response_model=DealOut)
def update_deal(
    deal_id: uuid.UUID,
    payload: DealUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    update_data = payload.model_dump(exclude_unset=True)
    if "next_contact_date" in update_data:
        # Nový/změněný termín - resetovat příznak, ať se pro něj (pokud
        # už je splatný) znovu vygeneruje notifikace.
        deal.next_contact_notified_at = None
    for field, value in update_data.items():
        setattr(deal, field, value)
    db.commit()
    db.refresh(deal)
    return deal


@router.delete("/{deal_id}", status_code=204)
def delete_deal(
    deal_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    db.delete(deal)
    db.commit()


@router.post("/{deal_id}/transition", response_model=DealOut)
def transition_deal(
    deal_id: uuid.UUID,
    payload: DealTransitionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Manuální přechod stavu Deal. Validuje povolené přechody a spouští
    vedlejší efekty (vytvoření Document apod.) podle business pravidel.
    Přechod Objednávka -> Zálohová faktura NENÍ dostupný zde - ten
    probíhá pouze automaticky přes /webhooks/esignature/{deal_id}.
    """
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return perform_transition(db, deal, payload.to_status)


class ManualOrderConfirmationRequest(BaseModel):
    note: str


@router.post("/{deal_id}/manual-order-confirmation", response_model=DealOut)
def manual_order_confirmation(
    deal_id: uuid.UUID,
    payload: ManualOrderConfirmationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Ruční přesun z "Objednávka" na "Zálohová faktura" pro případy, kdy
    objednávka byla potvrzena MIMO náš systém (typicky historické
    případy naimportované odjinud, kde neexistuje žádný náš dokument
    "Objednávka" k potvrzení přes veřejný odkaz). Normální cestou (přes
    e-signature webhook na skutečném dokumentu) tenhle přechod NEJDE
    obejít - tenhle endpoint je záměrně dostupný jen když u Dealu
    neexistuje žádný dokument typu Objednávka.
    """
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    if deal.status != DealStatus.OBJEDNAVKA:
        raise HTTPException(status_code=400, detail="Deal není ve stavu Objednávka")

    existing_document = (
        db.query(Document)
        .filter(Document.deal_id == deal_id, Document.document_type == DocumentType.OBJEDNAVKA)
        .first()
    )
    if existing_document:
        raise HTTPException(
            status_code=400,
            detail="U tohoto případu existuje dokument Objednávka - potvrzení musí proběhnout přes veřejný odkaz, ne ručně.",
        )

    if not payload.note or not payload.note.strip():
        raise HTTPException(status_code=400, detail="Je potřeba uvést poznámku (jak/kdy byla objednávka potvrzena).")

    deal.status = DealStatus.ZALOHOVA_FAKTURA
    note = DealNote(
        deal_id=deal.id,
        author_user_id=current_user.id,
        content=f"Objednávka potvrzena mimo systém: {payload.note.strip()}",
    )
    db.add(note)
    db.commit()
    db.refresh(deal)
    return deal
