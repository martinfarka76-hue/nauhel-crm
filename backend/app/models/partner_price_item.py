import uuid
from datetime import datetime
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class PartnerPriceItem(Base):
    """
    Položka ceníku partnera (firmy, která dodává vlastní dřevo a my jí
    fakturujeme jen službu - opálení/úpravu). Cena je konečná "Cena služby
    bez dopravy bez DPH" za m² - žádný materiál ani další marže se
    nepřipočítává, protože dřevo dodává partner zdarma.
    """
    __tablename__ = "partner_price_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)

    name = Column(String(255), nullable=False)  # např. "Atacama - STANDARD"
    wood_type = Column(String(100), nullable=True)  # např. "Borovice", "Modřín"
    dimensions = Column(String(50), nullable=True)  # např. "20x145"
    profile = Column(String(100), nullable=True)  # např. "Falcovaný (Z)"
    length = Column(String(50), nullable=True)  # např. "3/4/5"
    surface = Column(String(255), nullable=True)  # "Povrch" - např. "hluboce opálený - 100% černý"

    service_price_per_m2 = Column(Numeric(10, 2), nullable=False)  # Cena služby bez dopravy bez DPH

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    company = relationship("Company", back_populates="partner_price_items")
