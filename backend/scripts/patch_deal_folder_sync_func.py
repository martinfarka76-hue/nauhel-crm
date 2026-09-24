path = "app/core/deal_folder.py"
with open(path) as f:
    content = f.read()

# 1) Import generatoru certifikatu
old1 = "from app.core.delivery_note_pdf import generate_delivery_note_pdf"
new1 = '''from app.core.delivery_note_pdf import generate_delivery_note_pdf
from app.core.confirmation_certificate import generate_confirmation_certificate_pdf'''

count1 = content.count(old1)
if count1 != 1:
    print(f"CHYBA import: nalezeno {count1}x")
else:
    content = content.replace(old1, new1)

# 2) Nova funkce - vlozit pred sync_offer_pdf_to_sharepoint
old2 = "def sync_offer_pdf_to_sharepoint(db: Session, document: Document, deal: Deal) -> None:"
new2 = '''def sync_confirmation_to_sharepoint(db: Session, deal: Deal, document: Document, company: Company | None) -> None:
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


def sync_offer_pdf_to_sharepoint(db: Session, document: Document, deal: Deal) -> None:'''

count2 = content.count(old2)
if count2 != 1:
    print(f"CHYBA funkce: nalezeno {count2}x")
else:
    content = content.replace(old2, new2)

if count1 == 1 and count2 == 1:
    with open(path, 'w') as f:
        f.write(content)
    print("deal_folder.py (sync_confirmation) opraveno")
else:
    print("NIC nebylo zapsano kvuli chybe vyse")
