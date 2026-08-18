import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt
from passlib.context import CryptContext

# JWT_SECRET musí být nastaven v .env (viz .env.example)
SECRET_KEY = os.getenv("JWT_SECRET")
if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET není nastaven v prostředí (.env)")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 8 * 60  # 8 hodin - pracovní den

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    # Vyhazuje JWTError při neplatném/expirovaném tokenu - zachytává volající kód
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
