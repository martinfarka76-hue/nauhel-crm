"""
Endpointy pro MCP integraci (Claude jako čtenář/zapisovatel CRM dat).

Toto NENÍ samostatná byznys logika - jde o tenkou, read-first vrstvu nad
stejnými modely/pravidly, která používá zbytek CRM (žádné DB shortcuty,
žádná duplicitní logika). Autentizace je oddělená od uživatelského JWT
loginu (viz get_mcp_service) - jeden statický service token pro interní
mcp-server kontejner.

Rozsah (podle domluvené první verze, 9/2026):
- čtení dealů (pipeline) a jejich detailu, včetně firmy/kontaktu a
  dopočítaného váženého objemu
- vyhledání firmy podle názvu/IČO
- zápis poznámky k dealu (běžná poznámka, nebo jednoduchý úkol přes
  is_task/due_date na DealNote)

Záměrně NENÍ součástí: mazání čehokoliv, změna stavu dealu, změna ceníků/
bankovních údajů, odesílání závazných nabídek - to zůstává vyhrazené
uživatelskému UI, ve shodě s AI governance modelem CRM.
"""
import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import get_mcp_service
from app.models.company import Company
from app.models.contact import Contact
from app.models.deal import Deal
from app.models.deal_note import DealNote
from app.models.document import Document
from app.models.enums import DealStatus
from app.models.stage_config import StageConfig
from app.models.user import User

router = APIRouter(prefix="/api/mcp", tags=["mcp"], dependencies=[Depends(get_mcp_service)])


def _weighted_volume(deal: Deal, db: Session) -> Optional[Decimal]:
    """Cena × pravděpodobnost aktuálního stavu - stejný výpočet jako v UI (viz Deal model)."""
    if deal.price is None:
        return None
    stage = db.query(StageConfig).filter(StageConfig.stage_name == deal.status.value).first()
    if not stage:
        return None
    return (deal.price * Decimal(stage.probability_percent) / Decimal(100)).quantize(Decimal("1"))


class McpCompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    ico: Optional[str] = None


class McpContactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None


class McpDealListItem(BaseModel):
    id: uuid.UUID
    name: str
    status: DealStatus
    company_name: str
    price: Optional[Decimal] = None
    weighted_volume: Optional[Decimal] = None
    expected_close_date: Optional[date] = None
    next_contact_date: Optional[date] = None
    created_at: Optional[str] = None


class McpDealNoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    content: str
    is_task: Optional[bool] = None
    due_date: Optional[date] = None
    author_name: Optional[str] = None
    created_at: str


class McpDealDetail(BaseModel):
    id: uuid.UUID
    name: str
    status: DealStatus
    price: Optional[Decimal] = None
    weighted_volume: Optional[Decimal] = None
    expected_close_date: Optional[date] = None
    expected_invoice_date: Optional[date] = None
    next_contact_date: Optional[date] = None
    deposit_paid: bool
    created_at: Optional[str] = None
    company: McpCompanyOut
    contact: Optional[McpContactOut] = None
    documents: list[str]
    notes: list[McpDealNoteOut]


class McpDealNoteCreate(BaseModel):
    content: str
    is_task: Optional[bool] = None
    due_date: Optional[date] = None


@router.get("/deals", response_model=list[McpDealListItem])
def mcp_list_deals(
    status: Optional[DealStatus] = None,
    company_name: Optional[str] = Query(default=None, description="Hledá podle části názvu firmy (case-insensitive)"),
    db: Session = Depends(get_db),
):
    query = db.query(Deal)
    if status:
        query = query.filter(Deal.status == status)
    if company_name:
        query = query.join(Company).filter(Company.name.ilike(f"%{company_name}%"))
    deals = query.order_by(Deal.created_at.desc()).limit(200).all()

    result = []
    for deal in deals:
        result.append(
            McpDealListItem(
                id=deal.id,
                name=deal.name,
                status=deal.status,
                company_name=deal.company.name if deal.company else "",
                price=deal.price,
                weighted_volume=_weighted_volume(deal, db),
                expected_close_date=deal.expected_close_date,
                next_contact_date=deal.next_contact_date,
                created_at=deal.created_at.isoformat() if deal.created_at else None,
            )
        )
    return result


@router.get("/deals/{deal_id}", response_model=McpDealDetail)
def mcp_get_deal(deal_id: uuid.UUID, db: Session = Depends(get_db)):
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    notes = (
        db.query(DealNote)
        .filter(DealNote.deal_id == deal_id)
        .order_by(DealNote.created_at.desc())
        .all()
    )
    note_items = []
    for note in notes:
        author_name = None
        if note.author_user_id:
            author = db.query(User).filter(User.id == note.author_user_id).first()
            author_name = author.full_name if author else None
        note_items.append(
            McpDealNoteOut(
                id=note.id,
                content=note.content,
                is_task=note.is_task,
                due_date=note.due_date,
                author_name=author_name,
                created_at=note.created_at.isoformat(),
            )
        )

    documents = (
        db.query(Document)
        .filter(Document.deal_id == deal_id)
        .order_by(Document.created_at.desc())
        .all()
    )
    document_labels = [f"{doc.document_type.value} (v{doc.version})" for doc in documents]

    return McpDealDetail(
        id=deal.id,
        name=deal.name,
        status=deal.status,
        price=deal.price,
        weighted_volume=_weighted_volume(deal, db),
        expected_close_date=deal.expected_close_date,
        expected_invoice_date=deal.expected_invoice_date,
        next_contact_date=deal.next_contact_date,
        deposit_paid=deal.deposit_paid,
        created_at=deal.created_at.isoformat() if deal.created_at else None,
        company=McpCompanyOut.model_validate(deal.company),
        contact=McpContactOut.model_validate(deal.contact) if deal.contact else None,
        documents=document_labels,
        notes=note_items,
    )


@router.get("/companies", response_model=list[McpCompanyOut])
def mcp_search_companies(
    q: str = Query(..., min_length=2, description="Hledá v názvu firmy nebo IČO"),
    db: Session = Depends(get_db),
):
    companies = (
        db.query(Company)
        .filter((Company.name.ilike(f"%{q}%")) | (Company.ico.ilike(f"%{q}%")))
        .order_by(Company.name)
        .limit(50)
        .all()
    )
    return companies


@router.post("/deals/{deal_id}/notes", response_model=McpDealNoteOut, status_code=201)
def mcp_add_deal_note(deal_id: uuid.UUID, payload: McpDealNoteCreate, db: Session = Depends(get_db)):
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    if not payload.content.strip():
        raise HTTPException(status_code=422, detail="Poznámka nemůže být prázdná.")

    note = DealNote(
        deal_id=deal_id,
        author_user_id=None,  # zápis od Claude, ne od konkrétního uživatele - viz content prefix níže
        content=f"[Claude] {payload.content.strip()}",
        is_task=payload.is_task,
        due_date=payload.due_date,
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    return McpDealNoteOut(
        id=note.id,
        content=note.content,
        is_task=note.is_task,
        due_date=note.due_date,
        author_name="Claude",
        created_at=note.created_at.isoformat(),
    )
