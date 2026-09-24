path = "app/routers/document.py"
with open(path) as f:
    content = f.read()

patches = []

# 1) Nove importy
old1 = '''import uuid
import os
from pathlib import Path'''
new1 = '''import uuid
import os
import hashlib
import httpx
from pathlib import Path'''
patches.append((old1, new1))

old1b = '''from app.core.deal_folder import (
    sync_offer_pdf_to_sharepoint,
    sync_invoice_pdf_to_sharepoint,
    create_sharepoint_folder_for_deal,
    _build_document_filename,
)'''
new1b = '''from app.core.deal_folder import (
    sync_offer_pdf_to_sharepoint,
    sync_invoice_pdf_to_sharepoint,
    create_sharepoint_folder_for_deal,
    sync_confirmation_to_sharepoint,
    _build_document_filename,
)'''
patches.append((old1b, new1b))

# 2) Konstanta pro ulozeni VOP snapshotu + IP helper - vlozit pred
#    view_public_document
old2 = '''@router.get("/public/documents/{access_token}", response_model=DocumentViewCreateResult)
def view_public_document(access_token: str, request: Request, db: Session = Depends(get_db)):'''
new2 = '''VOP_SNAPSHOT_DIR = Path("/app/data/vop_snapshots")


def _get_client_ip(request: Request) -> str | None:
    """
    Zjisti skutecnou IP adresu klienta za reverse proxy (Cloudflare Tunnel).
    Cloudflare nastavuje CF-Connecting-IP na puvodni IP klienta; bez ni
    zkousi X-Forwarded-For (prvni hodnota v seznamu); jako posledni
    moznost primo request.client.host (uvnitr Docker site by to byla IP
    proxy, ne klienta).
    """
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip.strip()
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


@router.get("/public/documents/{access_token}", response_model=DocumentViewCreateResult)
def view_public_document(access_token: str, request: Request, db: Session = Depends(get_db)):'''
patches.append((old2, new2))

# 3) Oprava zaznamu IP u DocumentView (existujici sledovani zobrazeni)
old3 = '''    view = DocumentView(
        document_id=document.id,
        ip_address=request.client.host if request.client else None,
    )'''
new3 = '''    view = DocumentView(
        document_id=document.id,
        ip_address=_get_client_ip(request),
    )'''
patches.append((old3, new3))

# 4) confirm_document - pridat Request parametr
old4 = '''@router.post("/public/documents/{access_token}/confirm", response_model=DocumentConfirmResult)
def confirm_document(access_token: str, payload: DocumentConfirmRequest, db: Session = Depends(get_db)):'''
new4 = '''@router.post("/public/documents/{access_token}/confirm", response_model=DocumentConfirmResult)
def confirm_document(
    access_token: str,
    payload: DocumentConfirmRequest,
    request: Request,
    db: Session = Depends(get_db),
):'''
patches.append((old4, new4))

# 5) Zaznamenat IP + snapshot VOP pri prvnim potvrzeni, a po dokonceni
#    OBJEDNAVKA vetve nahrat certifikat na SharePoint
old5 = '''    if document.confirmed_at is None:
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
                perform_esignature_confirmation(db, deal)'''
new5 = '''    if document.confirmed_at is None:
        document.confirmed_at = datetime.utcnow()
        document.confirmed_by_name = payload.confirmed_by_name.strip()
        document.agreed_to_terms = True
        document.confirmation_ip_address = _get_client_ip(request)

        # Snapshot presneho zneni VOP v dobe potvrzeni (dukazni zaznam -
        # odkaz na VOP muze casem ukazovat na jiny obsah, tohle dokazuje
        # presne to, co zakaznik tehdy odsouhlasil). Nekriticka operace -
        # pokud stazeni selze, potvrzeni samotne se tim nezablokuje.
        if payload.vop_url:
            try:
                vop_resp = httpx.get(payload.vop_url, timeout=15.0)
                vop_resp.raise_for_status()
                vop_bytes = vop_resp.content
                vop_hash = hashlib.sha256(vop_bytes).hexdigest()
                VOP_SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
                vop_filename = f"{document.id}.pdf"
                (VOP_SNAPSHOT_DIR / vop_filename).write_bytes(vop_bytes)
                document.vop_snapshot_filename = vop_filename
                document.vop_snapshot_sha256 = vop_hash
            except Exception:
                pass

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

            if deal:
                sync_confirmation_to_sharepoint(db, deal, document, company)'''
patches.append((old5, new5))

ok = True
for i, (old, new) in enumerate(patches):
    count = content.count(old)
    if count != 1:
        print(f"CHYBA patch {i+1}: nalezeno {count}x (ocekavano 1x)")
        ok = False
    else:
        content = content.replace(old, new)

if ok:
    with open(path, 'w') as f:
        f.write(content)
    print("Vsech 6 patchu zapsano uspesne")
else:
    print("NIC nebylo zapsano kvuli chybe vyse")
