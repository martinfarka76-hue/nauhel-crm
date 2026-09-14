import os
import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.models.enums import UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Samostatná autentizace pro interní MCP integraci (Claude jako čtenář/
# zapisovatel CRM dat) - NENÍ to uživatelský JWT login, ale jeden statický
# service token z .env (MCP_SERVICE_TOKEN). Záměrně jednoduché: jde o
# jediného interního klienta (mcp-server kontejner), ne o veřejné API pro
# více uživatelů - OAuth flow s přihlašovací obrazovkou by byl zbytečná
# komplexita navíc.
_mcp_bearer_scheme = HTTPBearer(auto_error=False)


def get_mcp_service(
    credentials: HTTPAuthorizationCredentials = Depends(_mcp_bearer_scheme),
) -> None:
    expected_token = os.environ.get("MCP_SERVICE_TOKEN")
    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MCP integrace není nakonfigurována (MCP_SERVICE_TOKEN chybí v .env).",
        )
    if credentials is None or credentials.credentials != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Neplatný MCP service token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Neplatné nebo expirované přihlášení",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tato operace vyžaduje roli Admin",
        )
    return current_user
