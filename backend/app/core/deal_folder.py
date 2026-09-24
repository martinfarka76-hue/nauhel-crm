"""
Propojení mezi CRM entitami (Deal, Document) a SharePoint akcemi -
vytvoření složky zakázky, nahrání PDF nabídky/objednávky, nahrání faktury.
"""
import logging
import re
import datetime as _dt
from pathlib import Path

from sqlalchemy.orm import Session

from app.core import sharepoint
from app.core.folder_sequence import peek_next_folder_number, confirm_folder_number_used
from app.core.offer_pdf import generate_offer_pdf
from app.core.delivery_note_pdf import generate_delivery_note_pdf
from app.core.confirmation_certificate import generate_confirmation_certificate_pdf
from app.models.deal import Deal
from app.models.deal_attachment import DealAttachment
from app.models.document import Document
from app.models.company import Company
from app.models.contact import Contact
from app.models.user import User
from app.models.calculation import Calculation
from app.models.calculation_item import CalculationItem
from app.models.notification import Notification
from app.models.enums import DocumentType

logger = logging.getLogger("nauhel_crm.deal_folder")

ATTACHMENT_STORAGE_DIR = Path("/app/data/attachments")

DELIVERY_NOTE_STORAGE_DIR = Path("/app/data/delivery_notes")


def _sanitize_filename_part(text: str) -> str:
    """Odstraní znaky nevhodné pro název souboru na SharePointu/Windows.
    Windows/SharePoint navíc nepovoluje, aby název souboru/složky KONČIL
    tečkou nebo mezerou (typicky se stává u firem s "s.r.o." na konci
    názvu) - proto se to na konci ještě ořízne."""
    cleaned = re.sub(r'[\\/:*?"<>|]', "", text or "").strip()
    return cleaned.rstrip(". ")


def _build_document_filename(deal: Deal, company: Company | None, document_type_label: str) -> str:
    """
    Sestaví jednotný, čitelný název souboru ve formátu
    "{rok}_{číslo}_{Nabídka/Objednávka}_{Firma}_{Název zakázky}.pdf".
    Pokud Deal ještě nemá přidělené číslo složky, použije se "000".
    """
    year = deal.sharepoint_folder_year or _dt.date.today().year
    number = deal.sharepoint_folder_number or 0
    company_name = _sanitize_filename_part(company.name) if company else "Firma"
    deal_name = _sanitize_filename_part(deal.name)
    return f"{year}_{number:03d}_{document_type_label}_{company_name}_{deal_name}.pdf"


def create_sharepoint_folder_for_deal(db: Session, deal: Deal) -> None:
    """
    Vytvoří složku zakázky na SharePointu (idempotentní - pokud už Deal
    složku má, nic nedělá). Volat při přechodu na "Kvalifikovaný lead".
    """
    if deal.sharepoint_folder_url:
        return
    if not sharepoint.is_configured():
        logger.info("SharePoint není nakonfigurován - složka pro Deal %s se nevytváří", deal.id)
        return

    year = _dt.date.today().year
    number = peek_next_folder_number(db, year)
    company = db.query(Company).filter(Company.id == deal.company_id).first()
    company_name = _sanitize_filename_part(company.name) if company else "Firma"
    deal_name = _sanitize_filename_part(deal.name)
    folder_name = f"{year}_{number:03d}_{company_name}_{deal_name}"

    result = sharepoint.create_deal_folder(folder_name)
    if not result:
        return

    confirm_folder_number_used(db, year)

    deal.sharepoint_folder_year = year
    deal.sharepoint_folder_number = number
    deal.sharepoint_folder_url = result.get("web_url")
    deal.sharepoint_folder_id = result.get("folder_id")
    deal.sharepoint_drive_id = result.get("drive_id")
    deal.sharepoint_subfolder_nabidka_id = result.get("nabidka_subfolder_id")
    deal.sharepoint_subfolder_fakturace_id = result.get("fakturace_subfolder_id")
    deal.sharepoint_subfolder_poptavka_id = result.get("poptavka_subfolder_id")
    deal.sharepoint_subfolder_realizace_id = result.get("realizace_subfolder_id")
    deal.sharepoint_subfolder_smlouvy_id = result.get("smlouvy_subfolder_id")

    notification = Notification(
        notification_type="sharepoint_folder_created",
        message=f"Vytvořena SharePoint složka „{folder_name}“ - případ „{deal.name}“.",
        deal_id=deal.id,
    )
    db.add(notification)
    db.commit()

    sync_pending_attachments_for_deal(db, deal)


def sync_confirmation_to_sharepoint(db: Session, deal: Deal, document: Document, company: Company | None) -> None:
    """
    Nahraje certifikat potvrzeni objednavky (obsahujici jmeno, cas, IP
    adresu a otisk VOP) do podslozky "06_Smlouvy a specifikace" na
    SharePointu - dukazni zaznam pro pripad sporu/soudniho reseni. Volat
    hned po uspesnem potvrzeni dokumentu zakaznikem.
    """
    if not deal.sharepoint_drive_id or not deal.sharepoint_subfolder_smlouvy_id:
        return
    try:
        pdf_bytes = generate_confirmation_certificate_pdf(document, deal, company)
    except Exception:
        logger.exception("Generovani certifikatu potvrzeni selhalo pro Document %s", document.id)
        return

    filename = f"Potvrzeni_objednavky_{document.id}.pdf"
    sharepoint.upload_file_to_folder(
        deal.sharepoint_drive_id, deal.sharepoint_subfolder_smlouvy_id, filename, pdf_bytes
    )


def sync_offer_pdf_to_sharepoint(db: Session, document: Document, deal: Deal) -> None:
    """Vygeneruje PDF Nabídky/Objednávky a nahraje ho do podsložky 02_Nabídka."""
    if document.document_type not in (DocumentType.NABIDKA, DocumentType.OBJEDNAVKA):
        return
    if not deal.sharepoint_drive_id or not deal.sharepoint_subfolder_nabidka_id:
        return

    try:
        company = db.query(Company).filter(Company.id == deal.company_id).first()
        calc = db.query(Calculation).filter(Calculation.id == document.calculation_id).first()
        items = []
        if calc:
            items = (
                db.query(CalculationItem)
                .filter(CalculationItem.calculation_id == calc.id)
                .order_by(CalculationItem.display_order)
                .all()
            )

        pdf_bytes = generate_offer_pdf(document, deal, company, calc, items)
        type_label = document.document_type.value
        filename = _build_document_filename(deal, company, type_label)
        uploaded = sharepoint.upload_file_to_folder(
            deal.sharepoint_drive_id, deal.sharepoint_subfolder_nabidka_id, filename, pdf_bytes
        )
        if uploaded:
            notification = Notification(
                notification_type="sharepoint_document_synced",
                message=(
                    f"{type_label} (v{document.version}) nahrána na SharePoint - "
                    f"případ „{deal.name}“."
                ),
                deal_id=deal.id,
                document_id=document.id,
            )
            db.add(notification)
            db.commit()
    except Exception:
        logger.exception("Generování/nahrání PDF nabídky selhalo pro Document %s", document.id)


def sync_invoice_pdf_to_sharepoint(db: Session, deal: Deal, document: Document, filename: str, content_bytes: bytes) -> None:
    """Nahraje ručně nahranou fakturu i do podsložky 04_Fakturace na SharePointu."""
    if not deal.sharepoint_drive_id or not deal.sharepoint_subfolder_fakturace_id:
        return
    uploaded = sharepoint.upload_file_to_folder(
        deal.sharepoint_drive_id, deal.sharepoint_subfolder_fakturace_id, filename, content_bytes
    )
    if uploaded:
        notification = Notification(
            notification_type="sharepoint_document_synced",
            message=f"{document.document_type.value} nahrána na SharePoint - případ „{deal.name}“.",
            deal_id=deal.id,
            document_id=document.id,
        )
        db.add(notification)
        db.commit()


def sync_attachment_to_sharepoint(db: Session, deal: Deal, attachment: "DealAttachment", content_bytes: bytes) -> None:
    """
    Nahraje přílohu k poptávce (výkres, dokumentace) do podsložky
    01_Poptávka a označí ji jako synchronizovanou (synced_to_sharepoint_at).
    Pokud Deal ještě nemá SharePoint složku, jen se tiše přeskočí - tenhle
    "dluh" se dožene později přes sync_pending_attachments_for_deal, jakmile
    složka vznikne (viz konec create_sharepoint_folder_for_deal).
    """
    if not deal.sharepoint_drive_id or not deal.sharepoint_subfolder_poptavka_id:
        return
    filename = attachment.original_filename
    uploaded = sharepoint.upload_file_to_folder(
        deal.sharepoint_drive_id, deal.sharepoint_subfolder_poptavka_id, filename, content_bytes
    )
    if uploaded:
        attachment.synced_to_sharepoint_at = _dt.datetime.utcnow()
        notification = Notification(
            notification_type="sharepoint_document_synced",
            message=f"Příloha „{filename}“ nahrána na SharePoint - případ „{deal.name}“.",
            deal_id=deal.id,
        )
        db.add(notification)
        db.commit()


def sync_pending_attachments_for_deal(db: Session, deal: Deal) -> None:
    """
    Volat hned po vytvoření SharePoint složky (na konci
    create_sharepoint_folder_for_deal) - dohledá přílohy, které byly
    nahrané ještě PŘED existencí složky (typicky ve stavu Lead/
    Kvalifikovaný lead), a nahraje je dodatečně. Bez tohohle by takové
    přílohy zůstaly na SharePointu navždy chybět, aniž by si toho někdo
    všiml (upload samotný žádnou chybu nehlásí).
    """
    if not deal.sharepoint_drive_id or not deal.sharepoint_subfolder_poptavka_id:
        return
    pending = (
        db.query(DealAttachment)
        .filter(DealAttachment.deal_id == deal.id, DealAttachment.synced_to_sharepoint_at.is_(None))
        .all()
    )
    for attachment in pending:
        file_path = ATTACHMENT_STORAGE_DIR / attachment.stored_filename
        if not file_path.exists():
            logger.warning(
                "Priloha %s (Deal %s) nenalezena na disku - preskakuji dodatecny SharePoint sync",
                attachment.id, deal.id,
            )
            continue
        content = file_path.read_bytes()
        sync_attachment_to_sharepoint(db, deal, attachment, content)


def generate_and_sync_delivery_note(db: Session, deal: Deal, document: Document) -> None:
    """
    Vygeneruje Dodací list (PDF, v brandovém designu) a uloží ho lokálně
    (aby šel stáhnout z CRM) a nahraje kopii do podsložky 03_Realizace
    na SharePointu. Nikdy nevyhazuje výjimku ven - selhání generování
    nemá zablokovat samotný přechod stavu Dealu.
    """
    try:
        company = db.query(Company).filter(Company.id == deal.company_id).first()
        contact = db.query(Contact).filter(Contact.id == deal.contact_id).first() if deal.contact_id else None
        owner = db.query(User).filter(User.id == deal.owner_user_id).first() if deal.owner_user_id else None

        pdf_bytes = generate_delivery_note_pdf(db, deal, company, contact, owner)

        DELIVERY_NOTE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        file_path = DELIVERY_NOTE_STORAGE_DIR / f"{document.id}.pdf"
        file_path.write_bytes(pdf_bytes)
        document.delivery_note_filename = file_path.name
        db.commit()

        if deal.sharepoint_drive_id and deal.sharepoint_subfolder_realizace_id:
            filename = _build_document_filename(deal, company, "Dodací list")
            uploaded = sharepoint.upload_file_to_folder(
                deal.sharepoint_drive_id, deal.sharepoint_subfolder_realizace_id, filename, pdf_bytes
            )
            if uploaded:
                notification = Notification(
                    notification_type="sharepoint_document_synced",
                    message=f"Dodací list nahrán na SharePoint - případ „{deal.name}“.",
                    deal_id=deal.id,
                    document_id=document.id,
                )
                db.add(notification)
                db.commit()
    except Exception:
        logger.exception("Generování/nahrání dodacího listu selhalo pro Deal %s", deal.id)
