from sqlalchemy import Column, String, Integer

from app.database import Base


class StageConfig(Base):
    """
    Globální konfigurace pipeline - pravděpodobnost uzavření pro každý stav.
    Umožňuje editaci pravděpodobností bez zásahu do kódu.
    """
    __tablename__ = "stage_config"

    stage_name = Column(String(50), primary_key=True)
    probability_percent = Column(Integer, nullable=False)
    display_order = Column(Integer, nullable=False)
