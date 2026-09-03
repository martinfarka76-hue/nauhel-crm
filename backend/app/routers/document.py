import uuid
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import get_current_user
from app.core.deal_transitions import perform_esignature_confirmation
from app.core.ms_graph import send_email
from app.core.customer_notifications import (
    notify_customer_document_created,
    SIGNATURE_HTML,
    _salutation_and_surname,
)
from app.core.deal_folder import (
    sync_offer_pdf_to_sharepoint,
    sync_invoice_pdf_to_sharepoint,
    create_sharepoint_folder_for_deal,
)
from app.models.document import Document
from app.models.document_view import DocumentView
from app.models.deal import Deal
from app.models.company import Company
from app.models.contact import Contact
from app.models.calculation import Calculation
from app.models.user import User
from app.models.enums import DocumentType, DealStatus
from app.models.notification import Notification
from app.schemas.document import (
    DocumentCreate,
    DocumentUpdate,
    DocumentOut,
    DocumentPublicOut,
    CalculationPublicOut,
    DocumentViewCreateResult,
    DocumentViewDurationUpdate,
    DocumentViewOut,
    DocumentConfirmRequest,
    DocumentConfirmResult,
)

router = APIRouter(tags=["documents"])


# --- Interní endpointy (vyžadují přihlášení pro zápis) ---

@router.get("/documents", response_model=list[DocumentOut])
def list_all_documents(
    document_type: Optional[DocumentType] = None,
    company_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Seznam všech dokumentů napříč všemi Deals - pro souhrnný přehled (nabídky/faktury/dodací listy)."""
    query = db.query(Document)
    if document_type:
        query = query.filter(Document.document_type == document_type)
    if company_id:
        query = query.join(Deal, Document.deal_id == Deal.id).filter(Deal.company_id == company_id)
    return query.order_by(Document.created_at.desc()).all()


@router.get("/deals/{deal_id}/documents", response_model=list[DocumentOut])
def list_documents_for_deal(
    deal_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    if not db.query(Deal).filter(Deal.id == deal_id).first():
        raise HTTPException(status_code=404, detail="Deal not found")
    return (
        db.query(Document)
        .filter(Document.deal_id == deal_id)
        .order_by(Document.created_at.desc())
        .all()
    )


@router.post("/deals/{deal_id}/documents", response_model=DocumentOut, status_code=201)
def create_document(
    deal_id: uuid.UUID,
    payload: DocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    document = Document(deal_id=deal_id, **payload.model_dump())
    db.add(document)

    # Vytvoření Nabídky implikuje, že se Deal dostal (aspoň) do fáze Nabídka -
    # pokud je ještě dřív v pipeline (Lead/Kvalifikovaný lead), posuň ho.
    # Nikdy needeláme krok zpět, pokud je Deal už dál (Objednávka a později) -
    # to je případ pro dodatečnou/opravnou verzi nabídky, ne pro vrácení stavu.
    if payload.document_type == DocumentType.NABIDKA and deal.status in (
        DealStatus.LEAD,
        DealStatus.KVALIFIKOVANY_LEAD,
    ):
        deal.status = DealStatus.NABIDKA

    if payload.document_type == DocumentType.NABIDKA:
        create_sharepoint_folder_for_deal(db, deal)

    db.commit()
    db.refresh(document)
    notify_customer_document_created(db, document, deal)
    sync_offer_pdf_to_sharepoint(db, document, deal)
    return document


@router.get("/documents/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.put("/documents/{document_id}", response_model=DocumentOut)
def update_document(
    document_id: uuid.UUID,
    payload: DocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(document, field, value)
    db.commit()
    db.refresh(document)
    return document


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    db.delete(document)
    db.commit()


@router.get("/documents/{document_id}/views", response_model=list[DocumentViewOut])
def list_document_views(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Historie zobrazení dokumentu (kdy, jak dlouho, z jaké IP) - pro tracking v adminu."""
    if not db.query(Document).filter(Document.id == document_id).first():
        raise HTTPException(status_code=404, detail="Document not found")
    return (
        db.query(DocumentView)
        .filter(DocumentView.document_id == document_id)
        .order_by(DocumentView.viewed_at.desc())
        .all()
    )


# --- Veřejné endpointy (bez přihlášení) - pro frontend-public ---

@router.get("/public/documents/{access_token}", response_model=DocumentViewCreateResult)
def view_public_document(access_token: str, request: Request, db: Session = Depends(get_db)):
    document = db.query(Document).filter(Document.access_token == access_token).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    deal = db.query(Deal).filter(Deal.id == document.deal_id).first()
    company = db.query(Company).filter(Company.id == deal.company_id).first()

    calculation_public = None
    if document.calculation_id:
        calc = db.query(Calculation).filter(Calculation.id == document.calculation_id).first()
        if calc:
            calculation_public = CalculationPublicOut.model_validate(calc)

    public_document = DocumentPublicOut(
        id=document.id,
        document_type=document.document_type,
        version=document.version,
        created_at=document.created_at,
        confirmed_at=document.confirmed_at,
        confirmed_by_name=document.confirmed_by_name,
        company_name=company.name,
        company_ico=company.ico,
        company_dic=company.dic,
        company_address=company.address,
        deal_name=deal.name,
        calculation=calculation_public,
        has_invoice_pdf=bool(document.invoice_pdf_filename),
    )

    # Zaloguj zobrazení - IP z requestu (za reverse proxy by šlo číst X-Forwarded-For,
    # zatím jednoduše přímo z klienta)
    is_first_view = (
        db.query(DocumentView).filter(DocumentView.document_id == document.id).count() == 0
    )

    view = DocumentView(
        document_id=document.id,
        ip_address=request.client.host if request.client else None,
    )
    db.add(view)

    if is_first_view:
        notification = Notification(
            notification_type="document_first_viewed",
            message=f"{document.document_type} byla poprvé zobrazena zákazníkem - případ „{deal.name}“ ({company.name}).",
            deal_id=deal.id,
            document_id=document.id,
        )
        db.add(notification)

    db.commit()
    db.refresh(view)

    return DocumentViewCreateResult(document=public_document, view_id=view.id)


@router.patch("/public/documents/{access_token}/views/{view_id}", status_code=204)
def update_view_duration(
    access_token: str,
    view_id: uuid.UUID,
    payload: DocumentViewDurationUpdate,
    db: Session = Depends(get_db),
):
    document = db.query(Document).filter(Document.access_token == access_token).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    view = (
        db.query(DocumentView)
        .filter(DocumentView.id == view_id, DocumentView.document_id == document.id)
        .first()
    )
    if not view:
        raise HTTPException(status_code=404, detail="View record not found")

    view.duration_seconds = payload.duration_seconds
    db.commit()


@router.post("/public/documents/{access_token}/confirm", response_model=DocumentConfirmResult)
def confirm_document(access_token: str, payload: DocumentConfirmRequest, db: Session = Depends(get_db)):
    """
    Elektronické potvrzení objednávky zákazníkem přes veřejný odkaz -
    vlastní "domácí" náhrada e-signature, dokud není vybrán konkrétní
    externí nástroj. Vyžaduje zadání celého jména (jednoduché posílení
    důkazní hodnoty oproti pouhému kliknutí, byť nejde o kvalifikovaný
    elektronický podpis ve smyslu eIDAS). Relevantní hlavně pro dokumenty
    typu Objednávka: pokud je Deal stále ve stavu "Objednávka", automaticky
    spustí stejný přechod jako externí e-signature webhook (-> Zálohová
    faktura). Idempotentní - opakované volání po prvním potvrzení nic
    nerozbije (jméno z prvního potvrzení se zachová).
    """
    document = db.query(Document).filter(Document.access_token == access_token).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if not payload.confirmed_by_name or not payload.confirmed_by_name.strip():
        raise HTTPException(status_code=422, detail="Je potřeba uvést celé jméno potvrzující osoby.")

    if not payload.agreed_to_terms:
        raise HTTPException(
            status_code=422,
            detail="Je potřeba potvrdit souhlas se Všeobecnými obchodními podmínkami.",
        )

    if document.confirmed_at is None:
        document.confirmed_at = datetime.utcnow()
        document.confirmed_by_name = payload.confirmed_by_name.strip()
        document.agreed_to_terms = True
        db.commit()
        db.refresh(document)

        deal = db.query(Deal).filter(Deal.id == document.deal_id).first()

        if document.document_type == DocumentType.OBJEDNAVKA:
            company = db.query(Company).filter(Company.id == deal.company_id).first() if deal else None
            notification = Notification(
                notification_type="order_confirmed",
                message=(
                    f"Objednávka potvrzena zákazníkem ({document.confirmed_by_name}) - "
                    f"případ „{deal.name}“ ({company.name if company else '—'})."
                ),
                deal_id=document.deal_id,
                document_id=document.id,
            )
            db.add(notification)
            db.commit()

            admin_email = os.environ.get("ADMIN_NOTIFICATION_EMAIL")
            if admin_email and deal:
                admin_base_url = os.environ.get("ADMIN_BASE_URL", "http://localhost:18081")
                deal_link = f"{admin_base_url}/deals/{document.deal_id}"
                body_html = (
                    f"<p><strong>Objednávka byla potvrzena zákazníkem.</strong></p>"
                    f"<p>Případ: {deal.name}<br>"
                    f"Firma: {company.name if company else '—'}<br>"
                    f"Potvrdil(a): {document.confirmed_by_name}<br>"
                    f"Datum: {document.confirmed_at.strftime('%d.%m.%Y %H:%M')}</p>"
                    f'<p><a href="{deal_link}">Otevřít případ v CRM</a></p>'
                    f"{SIGNATURE_HTML}"
                )
                send_email(admin_email, f"Objednávka potvrzena - {deal.name}", body_html)

            if deal and deal.status == DealStatus.OBJEDNAVKA:
                perform_esignature_confirmation(db, deal)

    return DocumentConfirmResult(
        confirmed=True,
        confirmed_at=document.confirmed_at,
        confirmed_by_name=document.confirmed_by_name,
    )


# --- Ruční nahrávání faktur (PDF) - dokud iDoklad integrace není znovu ---
# --- zapnutá, faktury se vystavují ručně a nahrávají se sem            ---

INVOICE_STORAGE_DIR = Path("/app/data/invoices")


def _invoice_file_path(document_id: uuid.UUID) -> Path:
    return INVOICE_STORAGE_DIR / f"{document_id}.pdf"


@router.post("/documents/{document_id}/invoice-pdf", response_model=DocumentOut)
async def upload_invoice_pdf(
    document_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Nahraje PDF fakturu (ručně vystavenou např. v iDokladu) k dokumentu."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.document_type not in (DocumentType.ZALOHOVA_FAKTURA, DocumentType.FINALNI_FAKTURA):
        raise HTTPException(
            status_code=400,
            detail="Fakturu lze nahrát jen k dokumentu typu Zálohová faktura nebo Finální faktura.",
        )
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=422, detail="Nahraný soubor musí být PDF.")

    INVOICE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    file_path = _invoice_file_path(document_id)
    content = await file.read()
    file_path.write_bytes(content)

    document.invoice_pdf_filename = file_path.name
    db.commit()
    db.refresh(document)

    deal = db.query(Deal).filter(Deal.id == document.deal_id).first()
    if deal:
        label = "zalohova-faktura" if document.document_type == DocumentType.ZALOHOVA_FAKTURA else "faktura"
        sync_invoice_pdf_to_sharepoint(db, deal, document, f"{label}-{deal.name}.pdf", content)
    return document


@router.get("/documents/{document_id}/invoice-pdf")
def download_invoice_pdf(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stažení nahrané faktury - interní, vyžaduje přihlášení."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document or not document.invoice_pdf_filename:
        raise HTTPException(status_code=404, detail="Invoice PDF not found")
    file_path = _invoice_file_path(document_id)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Invoice PDF file missing on disk")
    return FileResponse(file_path, media_type="application/pdf", filename=file_path.name)


DELIVERY_NOTE_STORAGE_DIR = Path("/app/data/delivery_notes")


@router.get("/documents/{document_id}/delivery-note")
def download_delivery_note(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stažení automaticky vygenerovaného dodacího listu (Word .docx)."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document or not document.delivery_note_filename:
        raise HTTPException(status_code=404, detail="Delivery note not found")
    file_path = DELIVERY_NOTE_STORAGE_DIR / document.delivery_note_filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Delivery note file missing on disk")
    return FileResponse(
        file_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"Dodaci_list_{document.deal_id}.docx",
    )


@router.get("/public/documents/{access_token}/invoice-pdf")
def download_invoice_pdf_public(access_token: str, db: Session = Depends(get_db)):
    """Stažení nahrané faktury - veřejné, chráněné jen náhodným tokenem v odkazu."""
    document = db.query(Document).filter(Document.access_token == access_token).first()
    if not document or not document.invoice_pdf_filename:
        raise HTTPException(status_code=404, detail="Invoice PDF not found")
    file_path = _invoice_file_path(document.id)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Invoice PDF file missing on disk")
    return FileResponse(file_path, media_type="application/pdf", filename=file_path.name)


@router.post("/documents/{document_id}/send-invoice-email", response_model=DocumentOut)
def send_invoice_email(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Pošle zákazníkovi email s odkazem na fakturu a přiloženým PDF. Vyžaduje,
    aby už byla faktura nahraná, a aby měl Deal přiřazený kontakt s emailem.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if not document.invoice_pdf_filename:
        raise HTTPException(status_code=400, detail="K dokumentu ještě není nahraná žádná faktura.")

    deal = db.query(Deal).filter(Deal.id == document.deal_id).first()
    if not deal or not deal.contact_id:
        raise HTTPException(status_code=400, detail="Deal nemá přiřazený odpovědný kontakt.")

    contact = db.query(Contact).filter(Contact.id == deal.contact_id).first()
    if not contact or not contact.email:
        raise HTTPException(status_code=400, detail="Odpovědný kontakt nemá vyplněný email.")

    company = db.query(Company).filter(Company.id == deal.company_id).first()
    company_note = f" pro firmu {company.name}" if company else ""

    public_base_url = os.environ.get("PUBLIC_BASE_URL", "http://localhost:18082")
    link = f"{public_base_url}/n/{document.access_token}"

    label = "Zálohová faktura" if document.document_type == DocumentType.ZALOHOVA_FAKTURA else "Faktura"
    subject = f"{label} - {deal.name}"
    body_html = (
        f"<p>Dobrý den, {_salutation_and_surname(contact)},</p>"
        f"<p>zasíláme Vám {label.lower()} k zakázce „{deal.name}“{company_note}, "
        f"v příloze i na odkazu níže.</p>"
        f'<p><a href="{link}">Zobrazit fakturu online</a></p>'
        f"{SIGNATURE_HTML}"
    )

    file_path = _invoice_file_path(document_id)
    attachments = None
    if file_path.exists():
        attachments = [
            {
                "name": f"faktura-{deal.name}.pdf",
                "content_type": "application/pdf",
                "content_bytes": file_path.read_bytes(),
            }
        ]

    sent = send_email(contact.email, subject, body_html, attachments=attachments)
    if not sent:
        raise HTTPException(
            status_code=502,
            detail="Odeslání emailu selhalo - zkontroluj konfiguraci MS Graph nebo logy backendu.",
        )

    document.invoice_sent_at = datetime.utcnow()
    db.commit()
    db.refresh(document)
    return document
