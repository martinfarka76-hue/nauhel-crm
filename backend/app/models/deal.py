import uuid
from datetime import datetime
from sqlalchemy import Column, String, Numeric, Boolean, DateTime, Date, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.enums import DealStatus


class Deal(Base):
    """
    Centrální entita CRM - obchodní případ.
    Vážený objem (cena × pravděpodobnost stavu) se počítá v aplikační
    logice (ne jako DB sloupec), aby se automaticky přepočítal při
    změně StageConfig pravděpodobností.
    """
    __tablename__ = "deals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=True)
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    name = Column(String(255), nullable=False)
    status = Column(Enum(DealStatus), nullable=False, default=DealStatus.LEAD)

    price = Column(Numeric(12, 2), nullable=True)  # Cena
    expected_close_date = Column(Date, nullable=True)
    expected_invoice_date = Column(Date, nullable=True)
    deposit_paid = Column(Boolean, nullable=False, default=False)

    # SharePoint - odkaz na automaticky vytvořenou složku zakázky a ID
    # podsložek pro automatické nahrávání dokumentů (Nabídka, Faktury)
    sharepoint_folder_url = Column(String(500), nullable=True)
    sharepoint_folder_id = Column(String(255), nullable=True)
    sharepoint_drive_id = Column(String(255), nullable=True)
    sharepoint_subfolder_nabidka_id = Column(String(255), nullable=True)
    sharepoint_subfolder_fakturace_id = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    company = relationship("Company", back_populates="deals")
    contact = relationship("Contact", back_populates="deals")
    calculations = relationship("Calculation", back_populates="deal")
    documents = relationship("Document", back_populates="deal")
