import uuid
from datetime import datetime
from sqlalchemy import Column, String, Numeric, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class Calculation(Base):
    """
    Kalkulace zakázky. Přístup "snapshot" - Excel kalkulátor (parametrický
    cenový model specifický pro výrobu) zůstává zdrojem výpočtu; sem se
    ukládá výsledek pro konkrétní Deal.

    Typované sloupce pokrývají hodnoty, se kterými CRM často pracuje
    (zobrazení, filtrování, generování nabídky). raw_snapshot obsahuje
    kompletní kopii všech hodnot z Excelu pro danou kalkulaci, aby se
    nic neztratilo, i když se struktura Excelu časem změní.
    """
    __tablename__ = "calculations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deal_id = Column(UUID(as_uuid=True), ForeignKey("deals.id"), nullable=False)

    # Jen jedna aktivní kalkulace na Deal (vynuceno v aplikační logice při vytváření)
    is_active = Column(Boolean, nullable=False, default=True)

    # Klíčové vstupy
    product_line = Column(String(50), nullable=True)       # Atacama / Mirage / Ocaso
    wood_species = Column(String(255), nullable=True)
    area_m2 = Column(Numeric(10, 2), nullable=True)
    distance_km = Column(Numeric(10, 2), nullable=True)
    vat_rate = Column(Numeric(5, 4), nullable=True)         # např. 0.2100

    # Klíčové výstupy
    price_without_vat = Column(Numeric(12, 2), nullable=True)
    vat_amount = Column(Numeric(12, 2), nullable=True)
    price_with_vat = Column(Numeric(12, 2), nullable=True)
    unit_price_per_m2 = Column(Numeric(12, 2), nullable=True)
    margin_total = Column(Numeric(12, 2), nullable=True)

    # Kompletní snapshot všech hodnot z Excel kalkulace (flexibilní, bez nutnosti
    # migrace při každé změně struktury Excelu)
    raw_snapshot = Column(JSONB, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    deal = relationship("Deal", back_populates="calculations")
    documents = relationship("Document", back_populates="calculation")
