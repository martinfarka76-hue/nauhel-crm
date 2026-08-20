"""
Business logika přechodů stavů Deal pipeline.

Pravidla podle odsouhlasené architektury:
- Lead -> Kvalifikovaný lead: ruční
- Kvalifikovaný lead -> Nabídka: ruční, vyžaduje aktivní Calculation,
  automaticky vytvoří Document (Nabídka, verzovaná)
- Nabídka -> Objednávka: ruční ("Odeslat potvrzení objednávky")
- Objednávka -> Zálohová faktura: POUZE automaticky přes e-signature
  webhook, ne přes tento manuální endpoint
- Zálohová faktura -> Vyrobeno: ruční, vyžaduje deposit_paid=True,
  automaticky vytvoří Document (Dodací list)
- Vyrobeno -> Fakturováno: ruční, automaticky vytvoří Document
  (Finální faktura)
- Kterýkoli stav -> Ztraceno: ruční, vždy povoleno
"""
from datetime import date

from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.deal import Deal
from app.models.document import Document
from app.models.calculation import Calculation
from app.models.enums import DealStatus, DocumentType


# Stavy dosažitelné manuálně přes /transition endpoint (bez Ztraceno, to je vždy povoleno zvlášť)
MANUAL_TRANSITIONS: dict[DealStatus, set[DealStatus]] = {
    DealStatus.LEAD: {DealStatus.KVALIFIKOVANY_LEAD},
    DealStatus.KVALIFIKOVANY_LEAD: {DealStatus.NABIDKA},
    DealStatus.NABIDKA: {DealStatus.OBJEDNAVKA},
    # Objednávka -> Zálohová faktura NENÍ v manuálních přechodech - jen přes webhook
    DealStatus.OBJEDNAVKA: set(),
    DealStatus.ZALOHOVA_FAKTURA: {DealStatus.VYROBENO},
    DealStatus.VYROBENO: {DealStatus.FAKTUROVANO},
    DealStatus.FAKTUROVANO: set(),
    DealStatus.ZTRACENO: set(),
}


def _next_document_version(db: Session, deal_id, document_type: DocumentType) -> int:
    count = (
        db.query(Document)
        .filter(Document.deal_id == deal_id, Document.document_type == document_type)
        .count()
    )
    return count + 1


def perform_transition(db: Session, deal: Deal, to_status: DealStatus) -> Deal:
    """Provede a validuje manuální přechod stavu Deal. Vyhazuje HTTPException při neplatném přechodu."""

    # Ztraceno je vždy povoleno z jakéhokoli stavu
    if to_status == DealStatus.ZTRACENO:
        deal.status = DealStatus.ZTRACENO
        db.commit()
        db.refresh(deal)
        return deal

    allowed = MANUAL_TRANSITIONS.get(deal.status, set())
    if to_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Přechod ze stavu '{deal.status.value}' do '{to_status.value}' není povolen "
            f"(buď je to automatický přechod přes webhook, nebo je nedefinovaný).",
        )

    # Kvalifikovaný lead -> Nabídka: vyžaduje aktivní kalkulaci, vytváří Document
    if to_status == DealStatus.NABIDKA:
        active_calc = (
            db.query(Calculation)
            .filter(Calculation.deal_id == deal.id, Calculation.is_active.is_(True))
            .first()
        )
        if not active_calc:
            raise HTTPException(
                status_code=400,
                detail="Přechod do stavu 'Nabídka' vyžaduje existující aktivní kalkulaci.",
            )
        version = _next_document_version(db, deal.id, DocumentType.NABIDKA)
        document = Document(
            deal_id=deal.id,
            calculation_id=active_calc.id,
            document_type=DocumentType.NABIDKA,
            version=version,
        )
        db.add(document)

    # Nabídka -> Objednávka: zaznamenej skutečné datum uzavření (přestává být
    # jen odhad zadaný uživatelem, "zamkne se" na dnešní datum)
    if to_status == DealStatus.OBJEDNAVKA:
        deal.expected_close_date = date.today()

    # Zálohová faktura -> Vyrobeno: vyžaduje zaplacenou zálohu, vytváří Dodací list
    if to_status == DealStatus.VYROBENO:
        if not deal.deposit_paid:
            raise HTTPException(
                status_code=400,
                detail="Přechod do stavu 'Vyrobeno' vyžaduje zaplacenou zálohu (deposit_paid=true).",
            )
        document = Document(deal_id=deal.id, document_type=DocumentType.DODACI_LIST, version=1)
        db.add(document)

    # Vyrobeno -> Fakturováno: zaznamenej skutečné datum fakturace, vytváří finální fakturu
    if to_status == DealStatus.FAKTUROVANO:
        deal.expected_invoice_date = date.today()
        document = Document(deal_id=deal.id, document_type=DocumentType.FINALNI_FAKTURA, version=1)
        db.add(document)

    deal.status = to_status
    db.commit()
    db.refresh(deal)
    return deal


def perform_esignature_confirmation(db: Session, deal: Deal) -> Deal:
    """
    Automatický přechod Objednávka -> Zálohová faktura po potvrzení
    e-signature webhookem. Záloha = 50 % ceny nabídky (výchozí, lze
    později ručně upravit přes běžný PUT /deals/{id}).
    """
    if deal.status != DealStatus.OBJEDNAVKA:
        raise HTTPException(
            status_code=400,
            detail=f"E-signature webhook očekává Deal ve stavu 'Objednávka', "
            f"aktuální stav je '{deal.status.value}'.",
        )

    document = Document(deal_id=deal.id, document_type=DocumentType.ZALOHOVA_FAKTURA, version=1)
    db.add(document)

    deal.status = DealStatus.ZALOHOVA_FAKTURA
    db.commit()
    db.refresh(deal)
    return deal
