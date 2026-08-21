import uuid
from datetime import datetime
from sqlalchemy import Column, String, Numeric, DateTime
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class WoodSpecies(Base):
    """
    Databáze dřevin (palubek) - nákupní ceny a rozměry. Slouží k rychlému
    předvyplnění materiálové položky kalkulace, ne k automatickému
    dopočtu celé nabídky (tu pořád tvoří uživatel ručně přidáváním
    položek - viz CalculationItem).
    """
    __tablename__ = "wood_species"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    width_mm = Column(Numeric(6, 1), nullable=True)
    width_effective_mm = Column(Numeric(6, 1), nullable=True)
    length_mm = Column(Numeric(7, 1), nullable=True)
    thickness_mm = Column(Numeric(6, 1), nullable=True)
    purchase_price_per_m2 = Column(Numeric(10, 2), nullable=True)  # cena bez DPH
    supplier = Column(String(255), nullable=True)
    notes = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
