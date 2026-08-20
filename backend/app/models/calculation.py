import uuid
from datetime import datetime
from sqlalchemy import Column, String, Numeric, Boolean, DateTime, Date, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class Calculation(Base):
    """
    Kalkulace zakázky. Cena (price_without_vat/vat_amount/price_with_vat)
    se počítá automaticky jako součet CalculationItem řádků (po odečtení
    příslušné slevy dle kategorie) - viz app/core/calculation_totals.py.
    Tato pole jsou tedy READ-ONLY z pohledu API (nezapisují se přímo,
    přepočítávají se při každé změně položek nebo slev).
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

    # Slevy - aplikují se jen na položky dané kategorie (Doprava/Ostatní beze slevy)
    discount_material_percent = Column(Numeric(5, 2), nullable=False, default=0)
    discount_installation_percent = Column(Numeric(5, 2), nullable=False, default=0)

    # Vypočtené výstupy - NEZAPISOVAT přímo, přepočítává calculation_totals.py
    price_without_vat = Column(Numeric(12, 2), nullable=True)
    vat_amount = Column(Numeric(12, 2), nullable=True)
    price_with_vat = Column(Numeric(12, 2), nullable=True)
    unit_price_per_m2 = Column(Numeric(12, 2), nullable=True)
    margin_total = Column(Numeric(12, 2), nullable=True)

    # Platnost nabídky - do kdy je cena garantovaná
    valid_until = Column(Date, nullable=True)

    # Kompletní snapshot všech hodnot z Excel kalkulace (flexibilní, bez nutnosti
    # migrace při každé změně struktury Excelu)
    raw_snapshot = Column(JSONB, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    deal = relationship("Deal", back_populates="calculations")
    documents = relationship("Document", back_populates="calculation")
    items = relationship(
        "CalculationItem",
        back_populates="calculation",
        cascade="all, delete-orphan",
        order_by="CalculationItem.display_order",
    )
