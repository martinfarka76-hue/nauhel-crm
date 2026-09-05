import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.dependencies import get_current_user, require_admin
from app.core.security import hash_password
from app.models.user import User
from app.schemas.auth import UserOut, UserCreate, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])

AVATAR_STORAGE_DIR = Path("/app/data/avatars")


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Seznam uživatelů CRM - vrací VŠECHNY (i deaktivované), ať administrace
    (Nastavení) může zobrazit i neaktivní účty a případně je znovu aktivovat.
    Pro výběr vlastníka Dealu ve formulářích frontend sám filtruje jen
    is_active=true položky.
    """
    return db.query(User).order_by(User.full_name).all()


@router.post("", response_model=UserOut, status_code=201)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Uživatel s tímto emailem už existuje.")
    if len(payload.password) < 8:
        raise HTTPException(status_code=422, detail="Heslo musí mít alespoň 8 znaků.")

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


@router.post("/{user_id}/avatar", response_model=UserOut)
async def upload_user_avatar(
    user_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Nahraje fotku uživatele. Uživatel může nahrát svoji vlastní fotku,
    Admin může nahrát fotku komukoliv.
    """
    if current_user.id != user_id and current_user.role.value != "Admin":
        raise HTTPException(status_code=403, detail="Nemáš oprávnění nahrát fotku jinému uživateli.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=422, detail="Podporované formáty: JPEG, PNG, WEBP.")

    extension = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[file.content_type]

    AVATAR_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    file_path = AVATAR_STORAGE_DIR / f"{user_id}{extension}"
    content = await file.read()
    file_path.write_bytes(content)

    user.avatar_filename = file_path.name
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}/avatar")
def get_user_avatar(user_id: uuid.UUID, db: Session = Depends(get_db)):
    """Vrátí fotku uživatele - veřejné (jen náhled, chráněné neuhodnutelným UUID)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.avatar_filename:
        raise HTTPException(status_code=404, detail="Avatar not found")
    file_path = AVATAR_STORAGE_DIR / user.avatar_filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Avatar file missing on disk")
    return FileResponse(file_path)
