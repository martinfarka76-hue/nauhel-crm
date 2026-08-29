from sqlalchemy import Column, Integer

from app.database import Base


class FolderSequence(Base):
    """
    Pořadové číslo pro pojmenování složek na SharePointu (formát
    {rok}_{pořadové číslo}_{název případu}). Jeden řádek na rok.
    """
    __tablename__ = "folder_sequences"

    year = Column(Integer, primary_key=True)
    next_number = Column(Integer, nullable=False, default=1)
