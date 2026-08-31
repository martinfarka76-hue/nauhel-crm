from sqlalchemy.orm import Session

from app.models.folder_sequence import FolderSequence


def peek_next_folder_number(db: Session, year: int) -> int:
    """
    Vrátí příští volné pořadové číslo pro daný rok, ANIŽ by ho spotřebovala
    (počítadlo se nezvyšuje). Vytvoří řádek pro daný rok, pokud ještě
    neexistuje. Volat před pokusem o vytvoření složky na SharePointu.
    """
    seq = db.query(FolderSequence).filter(FolderSequence.year == year).first()
    if not seq:
        seq = FolderSequence(year=year, next_number=1)
        db.add(seq)
        db.commit()
        db.refresh(seq)
    return seq.next_number


def confirm_folder_number_used(db: Session, year: int) -> None:
    """
    Skutečně spotřebuje (zvýší) počítadlo - volat AŽ PO úspěšném vytvoření
    složky na SharePointu, ať při selhání nevznikne mezera v číslování.
    """
    seq = db.query(FolderSequence).filter(FolderSequence.year == year).first()
    if seq:
        seq.next_number += 1
        db.commit()
