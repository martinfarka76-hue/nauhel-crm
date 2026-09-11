import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    ico = Column(String(20), nullable=True)
    dic = Column(String(20), nullable=True)
    website = Column(String(255), nullable=True)
    address = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    # ID odpovídajícího kontaktu (odběratele) v iDokladu - jednou nalezené/
    # vytvořené se uloží sem, ať se příště nemusí znovu hledat podle IČO
    idoklad_contact_id = Column(Integer, nullable=True)
    # Partner = dodává vlastní dřevo, fakturujeme jen službu (opálení/úprava)
    # podle jeho vlastního ceníku - viz PartnerPriceItem.
    is_partner = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    contacts = relationship("Contact", back_populates="company", cascade="all, delete-orphan")
    deals = relationship("Deal", back_populates="company")
    partner_price_items = relationship("PartnerPriceItem", back_populates="company", cascade="all, delete-orphan")
