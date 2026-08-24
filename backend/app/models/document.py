import uuid
import secrets
from datetime import datetime
from sqlalchemy import Column, String, Integer, Numeric, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.enums import DocumentType


def generate_access_token() -> str:
    # Dlouhý náhodný token pro veřejné, nehádatelné URL nabídky
    return secrets.token_urlsafe(32)


class Document(Base):
    """
    Dokument navázaný na Deal (Nabídka/Objednávka/Zálohová faktura/
    Dodací list/Finální faktura). Nabídka je verzovaná (nová verze
    nemění status Dealu), ostatní typy nejsou.
    """
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deal_id = Column(UUID(as_uuid=True), ForeignKey("deals.id"), nullable=False)
    calculation_id = Column(UUID(as_uuid=True), ForeignKey("calculations.id"), nullable=True)

    document_type = Column(Enum(DocumentType), nullable=False)
    version = Column(Integer, nullable=False, default=1)  # relevantní hlavně pro Nabídku

    # Nehádatelný token pro veřejné zobrazení (frontend-public)
    access_token = Column(String(64), nullable=False, unique=True, default=generate_access_token)

    email_sent_at = Column(DateTime, nullable=True)
    reminder_sent_at = Column(DateTime, nullable=True)
    # Kdy zákazník elektronicky potvrdil (relevantní hlavně pro Objednávku -
    # vlastní "domácí" náhrada e-signature, dokud není vybrán konkrétní nástroj)
    confirmed_at = Column(DateTime, nullable=True)
    confirmed_by_name = Column(String(255), nullable=True)

    # Vyčíslená částka - relevantní hlavně pro Zálohová faktura (záloha
    # dle deposit_percent kalkulace) a Finální faktura (zbytek ceny)
    amount = Column(Numeric(12, 2), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    deal = relationship("Deal", back_populates="documents")
    calculation = relationship("Calculation", back_populates="documents")
    views = relationship("DocumentView", back_populates="document", cascade="all, delete-orphan")
