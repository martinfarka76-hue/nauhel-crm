import re
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.company import Company
from app.models.user import User
from app.schemas.company import CompanyCreate, CompanyUpdate, CompanyOut

router = APIRouter(prefix="/companies", tags=["companies"])


def _normalize_name(name: str) -> str:
    n = name.lower()
    n = re.sub(r"[.,]", "", n)
    n = re.sub(r"\s+", "", n)
    for suffix in ["sro", "spolsro", "as"]:
        if n.endswith(suffix):
            n = n[: -len(suffix)]
            break
    return n


@router.get("", response_model=list[CompanyOut])
def list_companies(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Company).order_by(Company.created_at.desc()).all()


@router.get("/check-duplicate", response_model=list[CompanyOut])
def check_duplicate_company(
    name: Optional[str] = None,
    ico: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Vrátí firmy, které vypadají jako možná duplicita zadaného názvu/IČO -
    jen pro zobrazení varování ve formuláři, nic neblokuje. Shoda podle IČO
    je jistá (přesná shoda). Shoda podle názvu je přibližná (bez velikosti
    písmen, mezer, teček a běžných právních přípon jako "s.r.o.").
    """
    if not name and not ico:
        return []

    matches = []
    if ico:
        matches.extend(db.query(Company).filter(Company.ico == ico).all())

    if name:
        target = _normalize_name(name)
        if target:
            candidates = db.query(Company).all()
            for c in candidates:
                if c in matches:
                    continue
                if _normalize_name(c.name) == target:
                    matches.append(c)

    return matches[:5]


@router.post("", response_model=CompanyOut, status_code=201)
def create_company(
    payload: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = Company(**payload.model_dump())
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


@router.get("/{company_id}", response_model=CompanyOut)
def get_company(company_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@router.put("/{company_id}", response_model=CompanyOut)
def update_company(
    company_id: uuid.UUID,
    payload: CompanyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(company, field, value)
    db.commit()
    db.refresh(company)
    return company


@router.delete("/{company_id}", status_code=204)
def delete_company(
    company_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    db.delete(company)
    db.commit()
