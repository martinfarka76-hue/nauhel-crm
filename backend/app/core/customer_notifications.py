"""
Emaily zákazníkovi s odkazem na veřejnou Nabídku/Objednávku. Odesílá se
kontaktu přiřazenému k Dealu (Deal.contact_id) - pokud kontakt není
přiřazený, nebo nemá vyplněný email, odeslání se tiše přeskočí.
"""
import os
import html

from sqlalchemy.orm import Session

from app.core.ms_graph import send_email
from app.models.document import Document
from app.models.deal import Deal
from app.models.contact import Contact
from app.models.company import Company
from app.models.calculation import Calculation
from app.models.enums import DocumentType

SIGNATURE_HTML = (
    "<p>NAUHEL s.r.o. · Ve Mlejnku 108, 257 65 Čechtice<br>"
    "telefon: +420 605 457 927 · email: "
    '<a href="mailto:info@nauhel.cz">info@nauhel.cz</a> · '
    '<a href="https://www.nauhel.cz">www.nauhel.cz</a></p>'
)


def _salutation_and_surname(contact: Contact) -> str:
    """
    Vrátí oslovení k použití v e-mailu. Pokud má kontakt ručně vyplněné
    Contact.salutation (např. "pane Vaňku" - správně skloněné), použije
    se přesně to. Jinak se sestaví odhad "pane/paní Příjmení": pohlaví se
    odhaduje podle koncovky křestního jména (končí na "a" -> paní, jinak
    pane) - příjmení zůstává v 1. pádě, ne skloňované.
    """
    if contact.salutation and contact.salutation.strip():
        return contact.salutation.strip()
    first_name = (contact.first_name or "").strip()
    salutation = "paní" if first_name.lower().endswith("a") else "pane"
    return f"{salutation} {contact.last_name}"


def notify_customer_document_created(db: Session, document: Document, deal: Deal) -> None:
    """
    Zavolat po vytvoření Document typu Nabídka nebo Objednávka. Pro
    ostatní typy (faktury, dodací listy) nic nedělá - ty zatím nemají
    veřejný obsah k odeslání.
    """
    if document.document_type not in (DocumentType.NABIDKA, DocumentType.OBJEDNAVKA):
        return
    if deal.skip_customer_emails:
        return
    if not deal.contact_id:
        return

    contact = db.query(Contact).filter(Contact.id == deal.contact_id).first()
    if not contact or not contact.email:
        return

    company = db.query(Company).filter(Company.id == deal.company_id).first()
    public_base_url = os.environ.get("PUBLIC_BASE_URL", "http://localhost:18082")
    link = f"{public_base_url}/n/{document.access_token}"
    company_note = f" pro firmu {company.name}" if company else ""

    if document.document_type == DocumentType.NABIDKA:
        calculation = (
            db.query(Calculation).filter(Calculation.id == document.calculation_id).first()
            if document.calculation_id
            else None
        )
        note_html = ""
        if calculation and calculation.customer_note and calculation.customer_note.strip():
            escaped_note = html.escape(calculation.customer_note.strip()).replace("\n", "<br>")
            note_html = f"<p>{escaped_note}</p>"

        subject = f"Nabídka od NAUHEL - {deal.name}"
        body_html = (
            f"<p>Dobrý den, {_salutation_and_surname(contact)},</p>"
            f"<p>zasíláme Vám cenovou nabídku na zakázku „{deal.name}“{company_note}.</p>"
            f"{note_html}"
            f'<p><a href="{link}">Zobrazit nabídku</a></p>'
            f"<p>V případě dotazů nás neváhejte kontaktovat.</p>"
            f"{SIGNATURE_HTML}"
        )
    else:  # OBJEDNAVKA
        subject = f"Potvrzení objednávky - {deal.name}"
        body_html = (
            f"<p>Dobrý den, {_salutation_and_surname(contact)},</p>"
            f"<p>na odkazu níže najdete shrnutí objednávky „{deal.name}“{company_note}. "
            f"Prosíme o její elektronické potvrzení kliknutím na tlačítko na stránce.</p>"
            f'<p><a href="{link}">Potvrdit objednávku</a></p>'
            f"{SIGNATURE_HTML}"
        )

    send_email(contact.email, subject, body_html)
