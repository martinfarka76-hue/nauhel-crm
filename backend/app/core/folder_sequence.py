import logging

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.folder_sequence import FolderSequence

logger = logging.getLogger("nauhel_crm.folder_sequence")


def peek_next_folder_number(db: Session, year: int) -> int:
    """
    Vrátí příští volné pořadové číslo pro daný rok, ANIŽ by ho spotřebovala
    (počítadlo se nezvyšuje). Vytvoří řádek pro daný rok, pokud ještě
    neexistuje. Volat před pokusem o vytvoření složky na SharePointu.

    SharePoint (složka 03_Zakázky) je AUTORITATIVNÍ zdroj pravdy - pokud
    je dostupný, počítadlo se nastaví přesně podle nejvyššího tam
    nalezeného čísla (ať už bylo naše počítadlo pozadu, nebo naopak
    příliš vysoko). Teprve když SharePoint není dostupný/nakonfigurovaný,
    použije se záložní kontrola proti databázi Dealů (jen chrání proti
    zaostávání, nikdy nesnižuje).
    """
    seq = db.query(FolderSequence).filter(FolderSequence.year == year).first()
    if not seq:
        seq = FolderSequence(year=year, next_number=1)
        db.add(seq)
        db.commit()
        db.refresh(seq)

    from app.core import sharepoint

    sharepoint_max = sharepoint.get_max_folder_number(year)
    if sharepoint_max is not None:
        authoritative_next = sharepoint_max + 1
        if authoritative_next != seq.next_number:
            logger.info(
                "Počítadlo složek pro rok %s nastaveno podle SharePointu (%s -> %s)",
                year, seq.next_number, authoritative_next,
            )
            seq.next_number = authoritative_next
            db.commit()
            db.refresh(seq)
        return seq.next_number

    # SharePoint nedostupný nebo nenakonfigurovaný - záložní kontrola
    # proti skutečně použitým číslům u existujících Dealů (nikdy
    # nesnižuje, jen chrání proti zaostávání počítadla za realitou).
    from app.models.deal import Deal

    max_used = (
        db.query(func.max(Deal.sharepoint_folder_number))
        .filter(Deal.sharepoint_folder_year == year)
        .scalar()
    )
    if max_used is not None and max_used >= seq.next_number:
        seq.next_number = max_used + 1
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
