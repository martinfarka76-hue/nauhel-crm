from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import verify_password, create_access_token
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import Token, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2PasswordRequestForm posílá email v poli "username"
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nesprávný email nebo heslo",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Účet je deaktivovaný")

    access_token = create_access_token(data={"sub": str(user.id), "role": user.role.value})
    return Token(access_token=access_token)


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
