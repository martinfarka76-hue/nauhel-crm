path = "app/routers/document.py"
with open(path) as f:
    content = f.read()

marker = '@router.post("/public/documents/{access_token}/confirm", response_model=DocumentConfirmResult)'
count = content.count(marker)
if count != 1:
    print(f"CHYBA: marker nalezen {count}x (ocekavano 1x)")
    raise SystemExit(1)

new_endpoint = '''@router.post("/documents/{document_id}/manual-confirm", response_model=DocumentConfirmResult)
def manual_confirm_document(
    document_id: uuid.UUID,
    payload: DocumentConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Rucni potvrzeni objednavky obchodnikem v CRM - pro pripady, kdy je u
    Dealu zapnute "Rucni formular" (skip_customer_emails) a zakaznik tedy
    nedostal e-mail s odkazem, ale potvrdil objednavku jinak (telefonicky,
    e-mailem apod. mimo system). Dela presne to same jako bezne potvrzeni
    zakaznikem pres verejny odkaz (prechod na Zalohova faktura, notifikace,
    e-mail adminovi) - jen bez nutnosti kopirovat odkaz a vyplnovat cizi
    formular. Idempotentni stejne jako verejne potvrzeni.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.document_type != DocumentType.OBJEDNAVKA:
        raise HTTPException(status_code=400, detail="Rucne potvrdit lze jen dokument typu Objednavka")
    if not payload.confirmed_by_name or not payload.confirmed_by_name.strip():
        raise HTTPException(status_code=422, detail="Je potreba uvest jmeno osoby, ktera objednavku potvrdila.")

    if document.confirmed_at is None:
        document.confirmed_at = datetime.utcnow()
        document.confirmed_by_name = payload.confirmed_by_name.strip()
        document.agreed_to_terms = True
        db.commit()
        db.refresh(document)

        deal = db.query(Deal).filter(Deal.id == document.deal_id).first()
        company = db.query(Company).filter(Company.id == deal.company_id).first() if deal else None

        notification = Notification(
            notification_type="order_confirmed",
            message=(
                f"Objednavka rucne potvrzena v CRM ({document.confirmed_by_name}) - "
                f"pripad \\u201e{deal.name}\\u201c ({company.name if company else '\\u2014'})."
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
                f"<p><strong>Objednavka byla rucne potvrzena v CRM.</strong></p>"
                f"<p>Pripad: {deal.name}<br>"
                f"Firma: {company.name if company else '\\u2014'}<br>"
                f"Potvrdil(a): {document.confirmed_by_name}<br>"
                f"Datum: {document.confirmed_at.strftime('%d.%m.%Y %H:%M')}</p>"
                f'<p><a href="{deal_link}">Otevrit pripad v CRM</a></p>'
                f"{SIGNATURE_HTML}"
            )
            send_email(admin_email, f"Objednavka rucne potvrzena - {deal.name}", body_html)

        if deal and deal.status == DealStatus.OBJEDNAVKA:
            perform_esignature_confirmation(db, deal)

    return DocumentConfirmResult(
        confirmed=True,
        confirmed_at=document.confirmed_at,
        confirmed_by_name=document.confirmed_by_name,
    )


''' + marker

content = content.replace(marker, new_endpoint, 1)

# Potrebujeme i importy Notification a DealStatus, pokud jeste nejsou
if "from app.models.notification import Notification" not in content:
    content = content.replace(
        "from app.models.calculation import Calculation",
        "from app.models.calculation import Calculation\nfrom app.models.notification import Notification",
        1,
    )
if "from app.models.enums import" in content:
    pass
else:
    content = content.replace(
        "from app.models.notification import Notification",
        "from app.models.notification import Notification\nfrom app.models.enums import DealStatus",
        1,
    )

with open(path, 'w') as f:
    f.write(content)
print("Endpoint pridan uspesne")
