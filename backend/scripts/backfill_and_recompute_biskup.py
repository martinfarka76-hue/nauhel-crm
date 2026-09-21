"""
Jednorazovy skript: pro Deal "DREVOSTAVBY BISKUP - Chata v Krystofove Udoli"
dohleda u polozek kalkulace prislusnou drevinu podle nazvu (parsovanim
"{nazev drevin} (Krycí plocha fasady: ...)"), dopini wood_species_id, a
prepocita cenu podle produktove rady "Atacama" - stejnym vzorcem, jaky
pouziva frontend (viz computeUnitPriceForSpecies).
"""
import sys
import re
sys.path.insert(0, ".")

from decimal import Decimal
from app.database import SessionLocal
from app.models.deal import Deal
from app.models.calculation import Calculation
from app.models.calculation_item import CalculationItem
from app.models.wood_species import WoodSpecies
from app.models.pricing_parameter import PricingParameter
from app.models.enums import ItemCategory
from app.core.calculation_totals import recompute_calculation_totals

DEAL_ID = "7bee17bc-c3a8-4f55-80a6-8ba9ca43830b"
PRODUCT_LINE = "Atacama"

db = SessionLocal()

params = {p.key: Decimal(str(p.value)) for p in db.query(PricingParameter).all()}

def compute_unit_price(species, product_line, material_quantity):
    material_quantity = Decimal(str(material_quantity))
    margin_material = params.get("margin_material", Decimal("0"))
    margin_vyroba = params.get("margin_vyroba", Decimal("0"))
    production_margin_effective = margin_vyroba if product_line == "Atacama" else margin_vyroba * Decimal("0.5")

    surcharge_key = f"surcharge_{product_line.lower()}_per_m2"
    surcharge = params.get(surcharge_key, Decimal("0"))
    production_base = params.get("production_base_per_m2", Decimal("0"))
    packaging_base = params.get("packaging_base_per_m2", Decimal("0"))
    transport_fixed = params.get("transport_fixed_from_supplier", Decimal("0"))
    purchase_price = Decimal(str(species.purchase_price_per_m2 or 0))

    vyroba_zaklad = material_quantity * (production_base + surcharge)
    baleni_celkem = material_quantity * packaging_base
    vyroba_s_marzi = (vyroba_zaklad + baleni_celkem) * (Decimal("1") + production_margin_effective)

    material_zaklad = material_quantity * purchase_price + transport_fixed
    material_s_marzi = material_zaklad * (Decimal("1") + margin_material)

    cena_celkem = material_s_marzi + vyroba_s_marzi
    if material_quantity > 0:
        return (cena_celkem / material_quantity).quantize(Decimal("0.01"))
    return Decimal("0")


deal = db.query(Deal).filter(Deal.id == DEAL_ID).first()
if not deal:
    print("CHYBA: Deal nenalezen")
    sys.exit(1)

calculations = db.query(Calculation).filter(Calculation.deal_id == deal.id).all()
species_list = db.query(WoodSpecies).all()
species_by_name = {s.name: s for s in species_list}

updated = 0
skipped = []

for calc in calculations:
    items = db.query(CalculationItem).filter(
        CalculationItem.calculation_id == calc.id,
        CalculationItem.category == ItemCategory.MATERIAL,
    ).all()

    for item in items:
        # Nazev je bud presne "{nazev drevin}" nebo "{nazev drevin} (Krycí plocha..."
        base_name = re.split(r"\s*\(Krycí plocha", item.name)[0].strip()
        species = species_by_name.get(base_name)
        if not species:
            skipped.append(item.name)
            continue

        item.wood_species_id = species.id
        new_price = compute_unit_price(species, PRODUCT_LINE, item.quantity)
        old_price = item.unit_price
        item.unit_price = new_price
        updated += 1
        print(f"  {base_name[:50]:50s} qty={item.quantity}  {old_price} Kc -> {new_price} Kc")

    recompute_calculation_totals(db, calc)

db.commit()

print()
print(f"Aktualizovano polozek: {updated}")
if skipped:
    print(f"Nenalezena drevina pro {len(skipped)} polozek (preskoceno beze zmeny):")
    for name in skipped:
        print(f"  - {name}")

db.close()
