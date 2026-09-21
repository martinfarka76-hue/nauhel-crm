import sys
sys.path.insert(0, ".")

from app.database import SessionLocal
from app.models.deal import Deal
from app.core import sharepoint

db = SessionLocal()

print("is_configured():", sharepoint.is_configured())

deal = db.query(Deal).filter(Deal.name == "Projekt Haly s.r.o.").first()
if not deal:
    print("CHYBA: Deal nenalezen")
    sys.exit(1)

print("Deal ID:", deal.id)
print("sharepoint_folder_url pred pokusem:", deal.sharepoint_folder_url)

try:
    result = sharepoint.create_deal_folder("TEST_DIAGNOSTIKA_smaz_me")
    print("Vysledek create_deal_folder:", result)
except Exception as e:
    print("VYJIMKA:", type(e).__name__, str(e))

db.close()
