import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.deal import Deal
from app.models.deal_note import DealNote
from app.models.user import User
from app.schemas.deal_note import DealNoteCreate, DealNoteOut

router = APIRouter(tags=["deal-notes"])


@router.get("/deals/{deal_id}/notes", response_model=list[DealNoteOut])
def list_deal_notes(
    deal_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Poznámky k Dealu, chronologicky - nejnovější první."""
    notes = (
        db.query(DealNote)
        .filter(DealNote.deal_id == deal_id)
        .order_by(DealNote.created_at.desc())
        .all()
    )
    result = []
    for note in notes:
        note_out = DealNoteOut.model_validate(note)
        if note.author_user_id:
            author = db.query(User).filter(User.id == note.author_user_id).first()
            note_out.author_name = author.full_name if author else None
        result.append(note_out)
    return result


@router.post("/deals/{deal_id}/notes", response_model=DealNoteOut, status_code=201)
def create_deal_note(
    deal_id: uuid.UUID,
    payload: DealNoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    if not payload.content.strip():
        raise HTTPException(status_code=422, detail="Poznámka nemůže být prázdná.")

    note = DealNote(deal_id=deal_id, author_user_id=current_user.id, content=payload.content.strip())
    db.add(note)
    db.commit()
    db.refresh(note)

    note_out = DealNoteOut.model_validate(note)
    note_out.author_name = current_user.full_name
    return note_out


@router.delete("/notes/{note_id}", status_code=204)
def delete_deal_note(
    note_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Smazání poznámky - jen autor sám může smazat vlastní poznámku (oprava překlepu apod.)."""
    note = db.query(DealNote).filter(DealNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if note.author_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Můžeš smazat jen vlastní poznámky.")
    db.delete(note)
    db.commit()
