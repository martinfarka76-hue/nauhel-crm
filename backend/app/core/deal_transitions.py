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
from app.core.customer_notifications import notify_customer_document_created
from app.core.invoice_issuing import issue_idoklad_invoice_for_document


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
        db.commit()
        db.refresh(document)
        notify_customer_document_created(db, document, deal)

    # Nabídka -> Objednávka: zaznamenej skutečné datum uzavření (přestává být
    # jen odhad zadaný uživatelem, "zamkne se" na dnešní datum). Vytváří
    # potvrzení objednávky (Document typu Objednávka), navázané na stejnou
    # aktivní kalkulaci jako naposledy vygenerovaná Nabídka.
    if to_status == DealStatus.OBJEDNAVKA:
        deal.expected_close_date = date.today()
        active_calc = (
            db.query(Calculation)
            .filter(Calculation.deal_id == deal.id, Calculation.is_active.is_(True))
            .first()
        )
        version = _next_document_version(db, deal.id, DocumentType.OBJEDNAVKA)
        document = Document(
            deal_id=deal.id,
            calculation_id=active_calc.id if active_calc else None,
            document_type=DocumentType.OBJEDNAVKA,
            version=version,
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        notify_customer_document_created(db, document, deal)

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
    # s částkou = celková cena aktivní kalkulace mínus již vyúčtovaná záloha
    if to_status == DealStatus.FAKTUROVANO:
        deal.expected_invoice_date = date.today()

        final_amount = None
        active_calc = (
            db.query(Calculation)
            .filter(Calculation.deal_id == deal.id, Calculation.is_active.is_(True))
            .first()
        )
        if active_calc and active_calc.price_with_vat is not None:
            zalohova_faktura = (
                db.query(Document)
                .filter(Document.deal_id == deal.id, Document.document_type == DocumentType.ZALOHOVA_FAKTURA)
                .order_by(Document.created_at.desc())
                .first()
            )
            deposit_already_invoiced = (
                zalohova_faktura.amount if zalohova_faktura and zalohova_faktura.amount else 0
            )
            final_amount = active_calc.price_with_vat - deposit_already_invoiced

        document = Document(
            deal_id=deal.id,
            calculation_id=active_calc.id if active_calc else None,
            document_type=DocumentType.FINALNI_FAKTURA,
            version=1,
            amount=final_amount,
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        issue_idoklad_invoice_for_document(db, document, deal)

    deal.status = to_status
    db.commit()
    db.refresh(deal)
    return deal


def perform_esignature_confirmation(db: Session, deal: Deal) -> Deal:
    """
    Automatický přechod Objednávka -> Zálohová faktura po elektronickém
    potvrzení objednávky zákazníkem (přes veřejnou stránku, nebo v
    budoucnu přes externí e-signature nástroj). Částka zálohy se počítá
    z aktivní kalkulace podle jejího nastaveného deposit_percent (výchozí
    50 %, upravitelné v editaci hlavičky kalkulace).
    """
    if deal.status != DealStatus.OBJEDNAVKA:
        raise HTTPException(
            status_code=400,
            detail=f"E-signature webhook očekává Deal ve stavu 'Objednávka', "
            f"aktuální stav je '{deal.status.value}'.",
        )

    active_calc = (
        db.query(Calculation)
        .filter(Calculation.deal_id == deal.id, Calculation.is_active.is_(True))
        .first()
    )

    deposit_amount = None
    if active_calc and active_calc.price_with_vat is not None:
        deposit_percent = active_calc.deposit_percent or 50
        deposit_amount = (active_calc.price_with_vat * deposit_percent) / 100

    document = Document(
        deal_id=deal.id,
        calculation_id=active_calc.id if active_calc else None,
        document_type=DocumentType.ZALOHOVA_FAKTURA,
        version=1,
        amount=deposit_amount,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    deal.status = DealStatus.ZALOHOVA_FAKTURA
    db.commit()
    db.refresh(deal)

    issue_idoklad_invoice_for_document(db, document, deal)
    return deal
