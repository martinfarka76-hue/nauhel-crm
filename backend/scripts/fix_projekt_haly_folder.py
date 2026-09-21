import sys
sys.path.insert(0, ".")

from app.database import SessionLocal
from app.models.deal import Deal
from app.core.deal_folder import create_sharepoint_folder_for_deal

db = SessionLocal()

deal = db.query(Deal).filter(Deal.name == "Projekt Haly s.r.o.").first()
if not deal:
    print("CHYBA: Deal nenalezen")
    sys.exit(1)

print("Pred opravou - sharepoint_folder_url:", deal.sharepoint_folder_url)

create_sharepoint_folder_for_deal(db, deal)

db.refresh(deal)
print("Po oprave - sharepoint_folder_url:", deal.sharepoint_folder_url)
print("Rok/cislo:", deal.sharepoint_folder_year, deal.sharepoint_folder_number)

db.close()
