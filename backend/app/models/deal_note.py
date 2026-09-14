import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Date, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class DealNote(Base):
    """
    Poznámka k obchodnímu případu - chronologický zápis aktivit/událostí.
    Poznámky se jen přidávají (nepřepisují se), ať je vidět historie toho,
    co se u případu dělo.

    is_task/due_date: jednoduché rozšíření poznámky na "úkol", bez nutnosti
    samostatné tabulky Tasks (viz rozhodnutí u zavedení MCP integrace,
    9/2026) - dokud se neukáže reálná potřeba vlastního životního cyklu
    úkolů (notifikace, přiřazení, nezávislost na dealu), stačí tenhle
    příznak na existující poznámce.
    """
    __tablename__ = "deal_notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deal_id = Column(UUID(as_uuid=True), ForeignKey("deals.id"), nullable=False)
    author_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    content = Column(Text, nullable=False)
    is_task = Column(Boolean, nullable=True)
    due_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
