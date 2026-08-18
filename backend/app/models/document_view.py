import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class DocumentView(Base):
    """
    Log zobrazení veřejného dokumentu (typicky Nabídky) - kdy byl otevřen,
    jak dlouho si ho zákazník prohlížel, z jaké IP. Umožňuje dodavateli
    (majiteli CRM) vidět aktivitu na nabídce.
    """
    __tablename__ = "document_views"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)

    viewed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    duration_seconds = Column(Integer, nullable=True)
    ip_address = Column(String(45), nullable=True)  # dost i pro IPv6

    document = relationship("Document", back_populates="views")
