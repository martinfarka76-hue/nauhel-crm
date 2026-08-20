"""
Jediný zdroj pravdy pro cenu Calculation: součet CalculationItem řádků
po odečtení příslušné slevy dle kategorie (Materiál/Práce mají vlastní
slevu, Doprava/Ostatní beze slevy - stejně jako v původním Excel modelu).

Volá se po každé změně položek nebo slev na Calculation. Pokud je
kalkulace aktivní, zároveň synchronizuje Deal.price, ať přehled (kanban)
vždy ukazuje aktuální cenu nabídky, ne zastaralý ruční odhad.
"""
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.models.calculation import Calculation
from app.models.calculation_item import CalculationItem
from app.models.deal import Deal
from app.models.enums import ItemCategory


def _round_crowns(value: Decimal) -> Decimal:
    """Zaokrouhlí na celé koruny - haléře se v ČR již reálně nepoužívají."""
    return value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def recompute_calculation_totals(db: Session, calculation: Calculation) -> Calculation:
    items = (
        db.query(CalculationItem)
        .filter(CalculationItem.calculation_id == calculation.id)
        .all()
    )

    discount_material = (calculation.discount_material_percent or Decimal("0")) / Decimal("100")
    discount_installation = (calculation.discount_installation_percent or Decimal("0")) / Decimal("100")

    total_without_vat = Decimal("0")
    for item in items:
        line_total = (item.quantity or Decimal("0")) * (item.unit_price or Decimal("0"))
        if item.category == ItemCategory.MATERIAL:
            line_total *= Decimal("1") - discount_material
        elif item.category == ItemCategory.PRACE:
            line_total *= Decimal("1") - discount_installation
        # Doprava a Ostatní beze slevy
        total_without_vat += line_total

    total_without_vat = _round_crowns(total_without_vat)
    vat_rate = calculation.vat_rate or Decimal("0")
    vat_amount = _round_crowns(total_without_vat * vat_rate)
    total_with_vat = total_without_vat + vat_amount

    calculation.price_without_vat = total_without_vat
    calculation.vat_amount = vat_amount
    calculation.price_with_vat = total_with_vat

    if calculation.area_m2 and calculation.area_m2 > 0:
        calculation.unit_price_per_m2 = _round_crowns(total_without_vat / calculation.area_m2)

    # Synchronizuj Deal.price s aktivní kalkulací, ať přehled (kanban) vždy
    # ukazuje aktuální cenu, ne zastaralý ruční odhad zadaný při vytvoření Dealu.
    if calculation.is_active:
        deal = db.query(Deal).filter(Deal.id == calculation.deal_id).first()
        if deal:
            deal.price = total_with_vat

    db.commit()
    db.refresh(calculation)
    return calculation
