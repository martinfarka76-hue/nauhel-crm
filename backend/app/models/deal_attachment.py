import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class DealAttachment(Base):
    """
    Obecná příloha k obchodnímu případu (výkresy, projektová dokumentace
    apod. - "Poptávka") - na rozdíl od Document (Nabídka/Faktury...) nemá
    verze ani veřejný přístup, je to jen prostý nahraný soubor.
    """
    __tablename__ = "deal_attachments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deal_id = Column(UUID(as_uuid=True), ForeignKey("deals.id"), nullable=False)
    stored_filename = Column(String(255), nullable=False)  # název souboru na disku (= {id}.pripona)
    original_filename = Column(String(255), nullable=False)  # název, jak ho nahrál uživatel
    content_type = Column(String(100), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    # Kdy se prilohu podarilo nahrat na SharePoint - NULL = jeste nikdy
    # (typicky proto, ze v dobe nahrani jeste neexistovala SharePoint
    # slozka Dealu; viz sync_pending_attachments_for_deal, ktera to
    # dohledava po vytvoreni slozky).
    synced_to_sharepoint_at = Column(DateTime, nullable=True)
