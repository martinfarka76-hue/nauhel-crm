"""
Naplní StageConfig, PricingParameter a WoodSpecies výchozími hodnotami,
pokud jsou tabulky prázdné. Spouští se jednou při startu aplikace
(idempotentní - kontroluje počet záznamů, nic nepřepisuje).
"""
from sqlalchemy.orm import Session

from app.models.stage_config import StageConfig
from app.models.pricing_parameter import PricingParameter
from app.models.wood_species import WoodSpecies

DEFAULT_PROBABILITIES = [
    ("Lead", 10, 1),
    ("Kvalifikovaný lead", 25, 2),
    ("Nabídka", 50, 3),
    ("Objednávka", 90, 4),
    ("Zálohová faktura", 95, 5),
    ("Vyrobeno", 98, 6),
    ("Fakturováno", 100, 7),
    ("Ztraceno", 0, 8),
]


def seed_stage_config(db: Session) -> None:
    if db.query(StageConfig).count() > 0:
        return
    for stage_name, probability, order in DEFAULT_PROBABILITIES:
        db.add(StageConfig(stage_name=stage_name, probability_percent=probability, display_order=order))
    db.commit()


# Výchozí prodejní parametry - odpovídá listu "Parametry" z Excel kalkulátoru
# (jen prodejní část, ne interní nákladový/mzdový model)
DEFAULT_PRICING_PARAMETERS = [
    ("vat_rate_default", "Výchozí sazba DPH", 0.21, "%"),
    ("fuel_price_per_km", "Cena/km – palivo", 4, "Kč/km"),
    ("driver_price_per_km", "Amortizace/řidič – platba/km", 15, "Kč/km"),
    ("transport_fixed_from_supplier", "Fixní náklad – doprava od dodavatele", 1000, "Kč"),
    ("transport_fixed_to_customer", "Fixní náklad – doprava k zákazníkovi", 1000, "Kč"),
    ("margin_material", "Marže – materiál", 0.21, "%"),
    ("margin_installation", "Marže – montáž", 0.30, "%"),
    ("surcharge_atacama_per_m2", "Příplatek výroby Atacama / m²", 214.44, "Kč/m²"),
    ("surcharge_mirage_per_m2", "Příplatek výroby Mirage / m²", 555.89, "Kč/m²"),
    ("surcharge_ocaso_per_m2", "Příplatek výroby Ocaso / m²", 555.89, "Kč/m²"),
    ("installation_price_per_m2", "Montáž fasádního obkladu – cena/m²", 682.5, "Kč/m²"),
]


def seed_pricing_parameters(db: Session) -> None:
    """
    Idempotentní po jednotlivých klíčích (ne jen "tabulka prázdná?") - ať
    se dají do budoucna přidávat další výchozí parametry, aniž by se
    musela mazat celá tabulka na existujících instalacích.
    """
    existing_keys = {row[0] for row in db.query(PricingParameter.key).all()}
    for key, label, value, unit in DEFAULT_PRICING_PARAMETERS:
        if key not in existing_keys:
            db.add(PricingParameter(key=key, label=label, value=value, unit=unit))
    db.commit()


# Výchozí dřeviny - výběr z Excel listu "DB dřevin" jako startovní sada,
# uživatel si může přidat/upravit/smazat další podle potřeby
DEFAULT_WOOD_SPECIES = [
    ("Smrk \"KLASIK\" 20x146 mm, délka 4000mm", 146, 140, 4000, 20, 260.70, "TIMBER PROFIL s.r.o."),
    ("Smrk \"Z\" 21x145, délka 4000mm", 146, 126, 4000, 21, 260.70, "TIMBER PROFIL s.r.o."),
    ("Sibiřský modřín \"RHOMBUS\" 21x120, délka 4000 mm", 121, 121, 4000, 21, 829.50, "TIMBER PROFIL s.r.o."),
    ("Modřín Evropský \"Z\" 20x145, délka 4000mm", 145, 125, 4000, 20, 440.00, "MZP"),
    ("Douglaska \"terasa\" 27x145, délka 4000mm", 145, 145, 4000, 20, 460.00, "MZP"),
    ("Accoya", 130, 125, 4000, 25, 1185.00, "ToTEM s.r.o."),
    ("Severská borovice \"KLASIK\" 20x146 mm, délka 4200 mm", 145, 135, 4200, 20, 282.03, "TIMBER PROFIL s.r.o."),
    ("Borovice \"Z\" 20x145, délka 4000mm", 145, 125, 4000, 20, 380.00, "MZP"),
]


def seed_wood_species(db: Session) -> None:
    if db.query(WoodSpecies).count() > 0:
        return
    for name, width, width_eff, length, thickness, price, supplier in DEFAULT_WOOD_SPECIES:
        db.add(
            WoodSpecies(
                name=name,
                width_mm=width,
                width_effective_mm=width_eff,
                length_mm=length,
                thickness_mm=thickness,
                purchase_price_per_m2=price,
                supplier=supplier,
            )
        )
    db.commit()
