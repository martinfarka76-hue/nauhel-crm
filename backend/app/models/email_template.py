import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime

from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class EmailTemplate(Base):
    """
    Šablona emailu pro automatizované odesílání (nabídka, reminder,
    potvrzení objednávky...). Proměnné v body/subject ve formátu
    {{promenna}}, nahrazovány při odesílání (backend nebo n8n).
    """
    __tablename__ = "email_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(String(100), nullable=False)  # např. "nabidka_odeslana", "reminder_7dni"
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
