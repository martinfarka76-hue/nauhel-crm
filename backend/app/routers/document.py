import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.document import Document
from app.models.document_view import DocumentView
from app.models.deal import Deal
from app.models.company import Company
from app.models.calculation import Calculation
from app.models.user import User
from app.schemas.document import (
    DocumentCreate,
    DocumentUpdate,
    DocumentOut,
    DocumentPublicOut,
    CalculationPublicOut,
    DocumentViewCreateResult,
    DocumentViewDurationUpdate,
)

router = APIRouter(tags=["documents"])


# --- Interní endpointy (vyžadují přihlášení pro zápis) ---

@router.get("/deals/{deal_id}/documents", response_model=list[DocumentOut])
def list_documents_for_deal(deal_id: uuid.UUID, db: Session = Depends(get_db)):
    if not db.query(Deal).filter(Deal.id == deal_id).first():
        raise HTTPException(status_code=404, detail="Deal not found")
    return (
        db.query(Document)
        .filter(Document.deal_id == deal_id)
        .order_by(Document.created_at.desc())
        .all()
    )


@router.post("/deals/{deal_id}/documents", response_model=DocumentOut, status_code=201)
def create_document(
    deal_id: uuid.UUID,
    payload: DocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not db.query(Deal).filter(Deal.id == deal_id).first():
        raise HTTPException(status_code=404, detail="Deal not found")

    document = Document(deal_id=deal_id, **payload.model_dump())
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@router.get("/documents/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.put("/documents/{document_id}", response_model=DocumentOut)
def update_document(
    document_id: uuid.UUID,
    payload: DocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(document, field, value)
    db.commit()
    db.refresh(document)
    return document


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    db.delete(document)
    db.commit()


# --- Veřejné endpointy (bez přihlášení) - pro frontend-public ---

@router.get("/public/documents/{access_token}", response_model=DocumentViewCreateResult)
def view_public_document(access_token: str, request: Request, db: Session = Depends(get_db)):
    document = db.query(Document).filter(Document.access_token == access_token).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    deal = db.query(Deal).filter(Deal.id == document.deal_id).first()
    company = db.query(Company).filter(Company.id == deal.company_id).first()

    calculation_public = None
    if document.calculation_id:
        calc = db.query(Calculation).filter(Calculation.id == document.calculation_id).first()
        if calc:
            calculation_public = CalculationPublicOut.model_validate(calc)

    public_document = DocumentPublicOut(
        id=document.id,
        document_type=document.document_type,
        version=document.version,
        created_at=document.created_at,
        company_name=company.name,
        deal_name=deal.name,
        calculation=calculation_public,
    )

    # Zaloguj zobrazení - IP z requestu (za reverse proxy by šlo číst X-Forwarded-For,
    # zatím jednoduše přímo z klienta)
    view = DocumentView(
        document_id=document.id,
        ip_address=request.client.host if request.client else None,
    )
    db.add(view)
    db.commit()
    db.refresh(view)

    return DocumentViewCreateResult(document=public_document, view_id=view.id)


@router.patch("/public/documents/{access_token}/views/{view_id}", status_code=204)
def update_view_duration(
    access_token: str,
    view_id: uuid.UUID,
    payload: DocumentViewDurationUpdate,
    db: Session = Depends(get_db),
):
    document = db.query(Document).filter(Document.access_token == access_token).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    view = (
        db.query(DocumentView)
        .filter(DocumentView.id == view_id, DocumentView.document_id == document.id)
        .first()
    )
    if not view:
        raise HTTPException(status_code=404, detail="View record not found")

    view.duration_seconds = payload.duration_seconds
    db.commit()
