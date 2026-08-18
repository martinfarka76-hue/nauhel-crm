import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base
from app.models.enums import UserRole


class User(Base):
    """
    Uživatel CRM (Admin nebo Obchodník). AI agent (Claude) NENÍ uživatel
    v této tabulce - přistupuje přes samostatný, odděleně řízený
    mechanismus s vlastní sadou oprávnění (viz architektura AI governance).
    """
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.OBCHODNIK)
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
