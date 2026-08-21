from sqlalchemy import Column, String, Numeric

from app.database import Base


class PricingParameter(Base):
    """
    Editovatelná konfigurace cenových parametrů (sazba za km, marže,
    příplatky produktových řad...) - obdoba listu "Parametry" z Excelu.
    Klíč/hodnota tabulka, ať se dá měnit bez zásahu do kódu.
    """
    __tablename__ = "pricing_parameters"

    key = Column(String(100), primary_key=True)
    label = Column(String(255), nullable=False)
    value = Column(Numeric(12, 4), nullable=False)
    unit = Column(String(50), nullable=True)
