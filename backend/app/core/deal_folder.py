"""
Propojení mezi CRM entitami (Deal, Document) a SharePoint akcemi -
vytvoření složky zakázky, nahrání PDF nabídky/objednávky, nahrání faktury.
"""
import logging
import re
import datetime as _dt

from sqlalchemy.orm import Session

from app.core import sharepoint
from app.core.folder_sequence import peek_next_folder_number, confirm_folder_number_used
from app.core.offer_pdf import generate_offer_pdf
from app.models.deal import Deal
from app.models.document import Document
from app.models.company import Company
from app.models.calculation import Calculation
from app.models.calculation_item import CalculationItem
from app.models.notification import Notification
from app.models.enums import DocumentType

logger = logging.getLogger("nauhel_crm.deal_folder")


def _sanitize_filename_part(text: str) -> str:
    """Odstraní znaky nevhodné pro název souboru na SharePointu/Windows."""
    return re.sub(r'[\\/:*?"<>|]', "", text or "").strip()


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

    notification = Notification(
        notification_type="sharepoint_folder_created",
        message=f"Vytvořena SharePoint složka „{folder_name}“ - případ „{deal.name}“.",
        deal_id=deal.id,
    )
    db.add(notification)
    db.commit()


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


def sync_attachment_to_sharepoint(db: Session, deal: Deal, filename: str, content_bytes: bytes) -> None:
    """Nahraje přílohu k poptávce (výkres, dokumentace) do podsložky 01_Poptávka."""
    if not deal.sharepoint_drive_id or not deal.sharepoint_subfolder_poptavka_id:
        return
    uploaded = sharepoint.upload_file_to_folder(
        deal.sharepoint_drive_id, deal.sharepoint_subfolder_poptavka_id, filename, content_bytes
    )
    if uploaded:
        notification = Notification(
            notification_type="sharepoint_document_synced",
            message=f"Příloha „{filename}“ nahrána na SharePoint - případ „{deal.name}“.",
            deal_id=deal.id,
        )
        db.add(notification)
        db.commit()
