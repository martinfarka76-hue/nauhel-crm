import uuid
from sqlalchemy import Column, String, Numeric, Integer, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.enums import ItemCategory


class CalculationItem(Base):
    """
    Řádková položka kalkulace (materiál, práce/montáž, doprava, ostatní).
    Součet položek (po odečtení příslušné slevy dle kategorie) je jediný
    zdroj pravdy pro cenu Calculation - viz app/core/calculation_totals.py.
    """
    __tablename__ = "calculation_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    calculation_id = Column(UUID(as_uuid=True), ForeignKey("calculations.id"), nullable=False)

    category = Column(Enum(ItemCategory), nullable=False)
    name = Column(String(255), nullable=False)
    unit = Column(String(20), nullable=True)  # m², bm, ks, kpl, zakázka...
    quantity = Column(Numeric(12, 3), nullable=False, default=0)
    unit_price = Column(Numeric(12, 2), nullable=False, default=0)
    display_order = Column(Integer, nullable=False, default=0)
    # Pokud polozka vznikla z "Predvyplnit z drevin", ulozi se sem ID te
    # dreviny - umoznuje pozdejsi "Prepocitat podle aktualni produktove
    # rady" bez nutnosti hadat, z ceho polozka vznikla. Rucne pridane
    # polozky (a polozky z cenikuu partnera) toto pole nemaji.
    wood_species_id = Column(UUID(as_uuid=True), ForeignKey("wood_species.id"), nullable=True)

    calculation = relationship("Calculation", back_populates="items")
