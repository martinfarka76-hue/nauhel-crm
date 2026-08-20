"""
Naplní StageConfig výchozími pravděpodobnostmi uzavření, pokud je tabulka
prázdná. Spouští se jednou při startu aplikace (idempotentní - kontroluje
počet záznamů, nic nepřepisuje, pokud už tam něco je).
"""
from sqlalchemy.orm import Session

from app.models.stage_config import StageConfig

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
