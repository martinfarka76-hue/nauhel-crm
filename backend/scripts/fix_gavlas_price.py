import sys
sys.path.insert(0, ".")
from app.database import SessionLocal
from app.models.calculation import Calculation
from app.core.calculation_totals import recompute_calculation_totals

DEAL_ID = "1c44cfd2-2e45-45d0-882b-d29660cd72b9"

db = SessionLocal()
calc = db.query(Calculation).filter(Calculation.deal_id == DEAL_ID, Calculation.is_active.is_(True)).first()
if not calc:
    print("CHYBA: aktivni kalkulace nenalezena")
else:
    recompute_calculation_totals(db, calc)
    db.refresh(calc)
    from app.models.deal import Deal
    deal = db.query(Deal).filter(Deal.id == DEAL_ID).first()
    print("Aktivni kalkulace cena:", calc.price_with_vat)
    print("Deal.price po oprave:", deal.price)
db.close()
