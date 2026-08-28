"""
Propojení mezi vznikem Document (Zálohová faktura / Finální faktura) a
skutečným vystavením daňového dokladu v iDokladu.
"""
import logging

from sqlalchemy.orm import Session

from app.core import idoklad
from app.models.document import Document
from app.models.deal import Deal
from app.models.company import Company
from app.models.calculation import Calculation
from app.models.enums import DocumentType

logger = logging.getLogger("nauhel_crm.invoice_issuing")


def issue_idoklad_invoice_for_document(db: Session, document: Document, deal: Deal) -> None:
    """
    Vystaví skutečnou fakturu v iDokladu pro Document typu Zálohová
    faktura nebo Finální faktura. Tiše se přeskočí (jen zaloguje), pokud
    iDoklad není nakonfigurovaný, nebo pokud cokoliv selže - nikdy
    nepřeruší běžný chod CRM kvůli chybě na straně iDokladu.
    """
    if document.document_type not in (DocumentType.ZALOHOVA_FAKTURA, DocumentType.FINALNI_FAKTURA):
        return
    if not idoklad.is_configured():
        logger.info("iDoklad není nakonfigurován - faktura pro Document %s se nevystaví", document.id)
        return
    if document.amount is None:
        logger.warning("Document %s nemá vyčíslenou částku - fakturu nelze vystavit", document.id)
        return

    company = db.query(Company).filter(Company.id == deal.company_id).first()
    if not company:
        logger.warning("Deal %s nemá přiřazenou firmu - fakturu nelze vystavit", deal.id)
        return

    # Najdi/vytvoř odpovídajícího odběratele v iDokladu, ulož si ID pro příště
    if company.idoklad_contact_id:
        purchaser_id = company.idoklad_contact_id
    else:
        purchaser_id = idoklad.find_or_create_contact(company.ico, company.name, company.address)
        if purchaser_id:
            company.idoklad_contact_id = purchaser_id
            db.commit()

    if not purchaser_id:
        logger.warning("Nepodařilo se najít/vytvořit odběratele v iDokladu pro firmu %s", company.name)
        return

    active_calc = (
        db.query(Calculation)
        .filter(Calculation.deal_id == deal.id, Calculation.is_active.is_(True))
        .first()
    )
    vat_rate = active_calc.vat_rate if active_calc and active_calc.vat_rate is not None else 0.21

    item_label = "Zálohová faktura" if document.document_type == DocumentType.ZALOHOVA_FAKTURA else "Faktura"
    item_name = f"{item_label} - {deal.name}"

    result = idoklad.create_issued_invoice(
        purchaser_id=purchaser_id,
        item_name=item_name,
        amount=float(document.amount),
        vat_rate=float(vat_rate),
        is_advance_invoice=(document.document_type == DocumentType.ZALOHOVA_FAKTURA),
    )
    if result:
        document.idoklad_invoice_id = result.get("id")
        document.idoklad_invoice_number = result.get("number")
        document.idoklad_pdf_url = result.get("pdf_url")
        db.commit()
