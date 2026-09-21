"""
Jednorazovy skript: dodatecne nahraje na SharePoint prilohu, ktera byla
nahrana JESTE PRED vytvorenim Nabidky (tedy pred existenci SharePoint
slozky) - v tu chvili se sync tise preskocil (viz
sync_attachment_to_sharepoint - vraci se, pokud Deal jeste nema
sharepoint_drive_id/sharepoint_subfolder_poptavka_id).
"""
import sys
from pathlib import Path
sys.path.insert(0, ".")

from app.database import SessionLocal
from app.models.deal import Deal
from app.core.deal_folder import sync_attachment_to_sharepoint

DEAL_ID = "7bee17bc-c3a8-4f55-80a6-8ba9ca43830b"
STORED_FILENAME = "65c02e33-1e6f-4e04-8d27-5d0a31f585ca.pdf"
ORIGINAL_FILENAME = "architektonicka_studie_Krystofovo_Udoli.pdf"
ATTACHMENT_STORAGE_DIR = Path("/app/data/attachments")

db = SessionLocal()

deal = db.query(Deal).filter(Deal.id == DEAL_ID).first()
if not deal:
    print("CHYBA: Deal nenalezen")
    sys.exit(1)

if not deal.sharepoint_drive_id or not deal.sharepoint_subfolder_poptavka_id:
    print("CHYBA: Deal jeste nema SharePoint slozku - nejde synchronizovat.")
    sys.exit(1)

file_path = ATTACHMENT_STORAGE_DIR / STORED_FILENAME
if not file_path.exists():
    print(f"CHYBA: soubor nenalezen na disku: {file_path}")
    sys.exit(1)

content = file_path.read_bytes()
print(f"Nahravam '{ORIGINAL_FILENAME}' ({len(content)} bytes)...")

sync_attachment_to_sharepoint(db, deal, ORIGINAL_FILENAME, content)

print("Hotovo - zkontroluj slozku 01_Poptavka na SharePointu.")

db.close()
