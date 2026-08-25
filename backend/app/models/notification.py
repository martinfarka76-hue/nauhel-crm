import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Notification(Base):
    """
    Obecná notifikace pro admin rozhraní - navrženo rozšiřitelně (string typ
    události, ne pevný enum), ať se dá později snadno přidat další typ
    (např. z fakturační integrace), bez nutnosti měnit strukturu databáze.
    Zatím generují: potvrzení objednávky, první zobrazení dokumentu.
    """
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    notification_type = Column(String(50), nullable=False)  # "order_confirmed" | "document_first_viewed" | ...
    message = Column(Text, nullable=False)
    deal_id = Column(UUID(as_uuid=True), ForeignKey("deals.id"), nullable=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
