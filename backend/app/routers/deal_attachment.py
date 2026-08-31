import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import get_current_user
from app.core.deal_folder import sync_attachment_to_sharepoint
from app.models.deal import Deal
from app.models.deal_attachment import DealAttachment
from app.models.user import User
from app.schemas.deal_attachment import DealAttachmentOut

router = APIRouter(tags=["deal-attachments"])

ATTACHMENT_STORAGE_DIR = Path("/app/data/attachments")


def _attachment_file_path(attachment_id: uuid.UUID, extension: str) -> Path:
    return ATTACHMENT_STORAGE_DIR / f"{attachment_id}{extension}"


@router.get("/deals/{deal_id}/attachments", response_model=list[DealAttachmentOut])
def list_deal_attachments(
    deal_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(DealAttachment)
        .filter(DealAttachment.deal_id == deal_id)
        .order_by(DealAttachment.uploaded_at.desc())
        .all()
    )


@router.post("/deals/{deal_id}/attachments", response_model=DealAttachmentOut, status_code=201)
async def upload_deal_attachment(
    deal_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Nahraje přílohu k poptávce (výkres, projektová dokumentace...) k Dealu."""
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    attachment_id = uuid.uuid4()
    original_name = file.filename or "priloha"
    extension = Path(original_name).suffix

    ATTACHMENT_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    file_path = _attachment_file_path(attachment_id, extension)
    content = await file.read()
    file_path.write_bytes(content)

    attachment = DealAttachment(
        id=attachment_id,
        deal_id=deal_id,
        stored_filename=file_path.name,
        original_filename=original_name,
        content_type=file.content_type,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    sync_attachment_to_sharepoint(db, deal, original_name, content)

    return attachment


@router.get("/attachments/{attachment_id}/download")
def download_deal_attachment(
    attachment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attachment = db.query(DealAttachment).filter(DealAttachment.id == attachment_id).first()
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    file_path = ATTACHMENT_STORAGE_DIR / attachment.stored_filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Attachment file missing on disk")
    return FileResponse(
        file_path,
        media_type=attachment.content_type or "application/octet-stream",
        filename=attachment.original_filename,
    )


@router.delete("/attachments/{attachment_id}", status_code=204)
def delete_deal_attachment(
    attachment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attachment = db.query(DealAttachment).filter(DealAttachment.id == attachment_id).first()
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    file_path = ATTACHMENT_STORAGE_DIR / attachment.stored_filename
    if file_path.exists():
        file_path.unlink()
    db.delete(attachment)
    db.commit()
