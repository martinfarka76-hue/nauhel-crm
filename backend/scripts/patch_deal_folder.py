path = "app/core/deal_folder.py"
with open(path) as f:
    content = f.read()

patches = []

# 1) sync_attachment_to_sharepoint - nyni bere attachment objekt (ne jen
#    filename), aby si mohla oznacit synced_to_sharepoint_at
old1 = '''def sync_attachment_to_sharepoint(db: Session, deal: Deal, filename: str, content_bytes: bytes) -> None:
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
        db.commit()'''
new1 = '''def sync_attachment_to_sharepoint(db: Session, deal: Deal, attachment: "DealAttachment", content_bytes: bytes) -> None:
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
        sync_attachment_to_sharepoint(db, deal, attachment, content)'''
patches.append((old1, new1))

# 2) Zavolat dohnani na konci create_sharepoint_folder_for_deal
old2 = '''    notification = Notification(
        notification_type="sharepoint_folder_created",
        message=f"Vytvořena SharePoint složka „{folder_name}“ - případ „{deal.name}“.",
        deal_id=deal.id,
    )
    db.add(notification)
    db.commit()'''
new2 = '''    notification = Notification(
        notification_type="sharepoint_folder_created",
        message=f"Vytvořena SharePoint složka „{folder_name}“ - případ „{deal.name}“.",
        deal_id=deal.id,
    )
    db.add(notification)
    db.commit()

    sync_pending_attachments_for_deal(db, deal)'''
patches.append((old2, new2))

ok = True
for i, (old, new) in enumerate(patches):
    count = content.count(old)
    if count != 1:
        print(f"CHYBA patch {i+1}: nalezeno {count}x (ocekavano 1x)")
        ok = False
    else:
        content = content.replace(old, new)

if not ok:
    print("NIC nebylo zapsano kvuli chybe vyse")
    import sys
    sys.exit(1)

# 3) Potrebne importy - DealAttachment, ATTACHMENT_STORAGE_DIR, _dt (datetime uz je asi importovane jako _dt, over)
needs_check = []
if "from app.models.deal_attachment import DealAttachment" not in content:
    # najdi radek s importem Deal a pridej hned za nej
    marker = "from app.models.deal import Deal"
    if marker in content:
        content = content.replace(marker, marker + "\nfrom app.models.deal_attachment import DealAttachment", 1)
    else:
        needs_check.append("Deal import marker nenalezen - over rucne import DealAttachment")

if "ATTACHMENT_STORAGE_DIR" not in content.split("def sync_attachment_to_sharepoint")[0]:
    anchor = 'logger = logging.getLogger("nauhel_crm.deal_folder")'
    if anchor in content:
        content = content.replace(
            anchor,
            anchor + '\n\nATTACHMENT_STORAGE_DIR = Path("/app/data/attachments")',
            1,
        )
    else:
        needs_check.append("logger kotva nenalezena - over rucne definici ATTACHMENT_STORAGE_DIR")

if "from pathlib import Path" not in content:
    content = "from pathlib import Path\n" + content

with open(path, 'w') as f:
    f.write(content)

print("Vsechny patche zapsany uspesne")
if needs_check:
    print("POZOR, over rucne:")
    for msg in needs_check:
        print(f"  - {msg}")
