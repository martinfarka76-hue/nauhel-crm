from sqlalchemy.orm import Session

from app.models.folder_sequence import FolderSequence


def get_next_folder_number(db: Session, year: int) -> int:
    """
    Vrátí další volné pořadové číslo pro danou rok a zvýší počítadlo.
    Vytvoří řádek pro daný rok, pokud ještě neexistuje.
    """
    seq = db.query(FolderSequence).filter(FolderSequence.year == year).first()
    if not seq:
        seq = FolderSequence(year=year, next_number=1)
        db.add(seq)
        db.flush()

    number = seq.next_number
    seq.next_number += 1
    db.commit()
    return number
